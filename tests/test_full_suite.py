import io
import json
import pytest
import numpy as np
from fastapi.testclient import TestClient
from app.main import app
from app.risk import assess_event
from app.analysis import compute_motion_ratio, compute_density_score

client = TestClient(app)

# ---------------------------------------------------------------------------
# 1. System Health & Status Tests
# ---------------------------------------------------------------------------

def test_health_endpoint():
    r = client.get('/health')
    assert r.status_code == 200
    data = r.json()
    assert data['status'] == 'ok'
    assert 'service' in data

def test_status_endpoint():
    r = client.get('/api/v1/status')
    assert r.status_code == 200
    data = r.json()
    assert data['api'] == 'ok'
    assert data['database'] == 'ok'
    assert 'detector_model' in data
    assert 'detector_device' in data
    assert 'detection_scope' in data

# ---------------------------------------------------------------------------
# 2. Farms CRUD Tests
# ---------------------------------------------------------------------------

def test_farm_crud_lifecycle():
    # 1. Create farm
    farm_data = {
        "name": "Green Meadows Test Farm",
        "location": "Sector 4, Greenfield",
        "contact_name": "Amina Khan",
        "contact_phone": "+91 9876543210",
        "notes": "Standard test farm for automated validation"
    }
    res_create = client.post('/api/v1/farms', json=farm_data)
    assert res_create.status_code == 201
    created_farm = res_create.json()
    farm_id = created_farm['id']
    assert created_farm['name'] == farm_data['name']
    assert created_farm['location'] == farm_data['location']

    # 2. List farms
    res_list = client.get('/api/v1/farms')
    assert res_list.status_code == 200
    farms = res_list.json()
    assert any(f['id'] == farm_id for f in farms)

    # 3. Retrieve farm by ID
    res_get = client.get(f'/api/v1/farms/{farm_id}')
    assert res_get.status_code == 200
    retrieved = res_get.json()
    assert retrieved['id'] == farm_id
    assert 'flocks' in retrieved

    # 4. Update farm
    update_data = {
        "name": "Green Meadows Farm (Updated)",
        "location": "Sector 5, Greenfield"
    }
    res_update = client.patch(f'/api/v1/farms/{farm_id}', json=update_data)
    assert res_update.status_code == 200
    updated = res_update.json()
    assert updated['name'] == update_data['name']
    assert updated['location'] == update_data['location']

# ---------------------------------------------------------------------------
# 3. Flocks CRUD Tests
# ---------------------------------------------------------------------------

def test_flock_crud_lifecycle():
    # First ensure a parent farm exists
    farm_res = client.post('/api/v1/farms', json={"name": "Flock Parent Farm", "location": "Unit 2"})
    assert farm_res.status_code == 201
    farm_id = farm_res.json()['id']

    # 1. Create flock
    flock_data = {
        "farm_id": farm_id,
        "name": "Broiler Batch A-102",
        "breed": "Cobb 500",
        "bird_count": 500,
        "age_days": 21,
        "housing_type": "Deep litter shed",
        "status": "active"
    }
    res_flock = client.post('/api/v1/flocks', json=flock_data)
    assert res_flock.status_code == 201
    flock = res_flock.json()
    flock_id = flock['id']
    assert flock['name'] == flock_data['name']
    assert flock['bird_count'] == 500

    # 2. List flocks
    res_list = client.get(f'/api/v1/flocks?farm_id={farm_id}')
    assert res_list.status_code == 200
    flocks = res_list.json()
    assert len(flocks) >= 1
    assert any(f['id'] == flock_id for f in flocks)

    # 3. Retrieve flock
    res_get = client.get(f'/api/v1/flocks/{flock_id}')
    assert res_get.status_code == 200
    details = res_get.json()
    assert details['id'] == flock_id
    assert 'recent_events' in details

    # 4. Update flock
    res_up = client.patch(f'/api/v1/flocks/{flock_id}', json={"bird_count": 498, "age_days": 22})
    assert res_up.status_code == 200
    assert res_up.json()['bird_count'] == 498
    assert res_up.json()['age_days'] == 22

def test_invalid_flock_creation():
    # Attempt to link flock to non-existent farm
    res = client.post('/api/v1/flocks', json={"farm_id": 999999, "name": "Orphan Flock"})
    assert res.status_code == 404

# ---------------------------------------------------------------------------
# 4. Health Events & Triage Rules Tests
# ---------------------------------------------------------------------------

def test_health_event_routine_triage():
    res = client.post('/api/v1/health-events', json={
        "signs": [],
        "sick_count": 0,
        "deaths": 0,
        "feed_change": "normal",
        "water_change": "normal",
        "notes": "Routine morning check, birds active"
    })
    assert res.status_code == 201
    data = res.json()
    assert data['risk_level'] == 'routine'
    assert data['is_diagnosis'] is False

def test_health_event_watch_triage():
    res = client.post('/api/v1/health-events', json={
        "signs": ["lethargy", "reduced appetite"],
        "sick_count": 2,
        "deaths": 0,
        "feed_change": "decreased",
        "water_change": "normal"
    })
    assert res.status_code == 201
    data = res.json()
    assert data['risk_level'] == 'watch'

def test_health_event_urgent_triage():
    res = client.post('/api/v1/health-events', json={
        "signs": ["breathing difficulty", "sudden collapse"],
        "sick_count": 5,
        "deaths": 3,
        "feed_change": "decreased",
        "water_change": "decreased",
        "notes": "Severe respiratory signs and multiple bird deaths"
    })
    assert res.status_code == 201
    data = res.json()
    assert data['risk_level'] == 'urgent'
    assert "Contact a poultry veterinarian" in data['advice']

def test_health_event_validation_negative_counts():
    res = client.post('/api/v1/health-events', json={
        "sick_count": -5,
        "deaths": 0
    })
    assert res.status_code == 422

# ---------------------------------------------------------------------------
# 5. Alerts Management Tests
# ---------------------------------------------------------------------------

def test_alerts_list_and_lifecycle():
    # Create an event that produces an alert
    client.post('/api/v1/health-events', json={
        "signs": ["bloody droppings"],
        "sick_count": 1,
        "deaths": 2
    })

    # List open alerts
    res = client.get('/api/v1/alerts?status=open')
    assert res.status_code == 200
    alerts = res.json()
    assert len(alerts) > 0
    target_alert = alerts[0]
    aid = target_alert['id']

    # Acknowledge alert
    res_ack = client.post(f'/api/v1/alerts/{aid}/acknowledge')
    assert res_ack.status_code == 200
    assert res_ack.json()['status'] == 'acknowledged'
    assert res_ack.json()['acknowledged_at'] is not None

    # Resolve alert
    res_res = client.post(f'/api/v1/alerts/{aid}/resolve')
    assert res_res.status_code == 200
    assert res_res.json()['status'] == 'resolved'
    assert res_res.json()['resolved_at'] is not None

# ---------------------------------------------------------------------------
# 6. Video Upload & Validation Tests
# ---------------------------------------------------------------------------

def test_video_upload_invalid_extension():
    fake_txt = io.BytesIO(b"This is not a video file.")
    res = client.post(
        '/api/v1/videos',
        files={"file": ("fake_file.txt", fake_txt, "text/plain")}
    )
    assert res.status_code == 415

def test_video_jobs_list():
    res = client.get('/api/v1/jobs')
    assert res.status_code == 200
    assert isinstance(res.json(), list)

# ---------------------------------------------------------------------------
# 7. Reports & CSV Exports Tests
# ---------------------------------------------------------------------------

def test_reports_summary():
    res = client.get('/api/v1/reports/summary')
    assert res.status_code == 200
    summary = res.json()
    assert 'farms' in summary
    assert 'flocks' in summary
    assert 'health_events' in summary
    assert 'total_jobs' in summary
    assert 'open_alerts' in summary
    assert 'accuracy_disclaimer' in summary

def test_reports_csv_exports():
    r_alerts = client.get('/api/v1/reports/alerts.csv')
    assert r_alerts.status_code == 200
    assert "text/csv" in r_alerts.headers.get("content-type", "")

    r_events = client.get('/api/v1/reports/events.csv')
    assert r_events.status_code == 200
    assert "text/csv" in r_events.headers.get("content-type", "")

    r_jobs = client.get('/api/v1/reports/jobs.csv')
    assert r_jobs.status_code == 200
    assert "text/csv" in r_jobs.headers.get("content-type", "")

# ---------------------------------------------------------------------------
# 8. Computer Vision Metric Functions Tests
# ---------------------------------------------------------------------------

def test_motion_ratio_identical_and_differing():
    blank = np.zeros((180, 320), dtype=np.uint8)
    assert compute_motion_ratio(blank, blank) == 0.0

    white = np.full((180, 320), 255, dtype=np.uint8)
    mr = compute_motion_ratio(blank, white)
    assert mr > 0.95

def test_density_score_bounds_and_coverage():
    # Empty box list
    assert compute_density_score([], 640, 360) == 0.0

    # Non-empty box
    boxes = [{"xyxy": [0, 0, 320, 180]}]
    score = compute_density_score(boxes, 640, 360)
    assert 0.20 <= score <= 0.30  # 1/4 of total area

    # Multiple overlapping boxes bounded by 1.0
    large_boxes = [
        {"xyxy": [0, 0, 640, 360]},
        {"xyxy": [10, 10, 600, 300]}
    ]
    assert compute_density_score(large_boxes, 640, 360) <= 1.0
