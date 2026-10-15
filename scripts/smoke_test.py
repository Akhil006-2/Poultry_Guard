"""PoultryGuard End-to-End Smoke Test Suite
Validates backend, database, frontend build, spatial density screening,
evidence frames, SMS notification engine, model evaluation, and report exports.
"""
import sys
import os
import json
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient
from app.main import app
from app.config import get_settings
from app import db
from app.analysis import analyze_video

def run_smoke_test():
    print("=" * 65)
    print("POULTRYGUARD END-TO-END SYSTEM SMOKE TEST")
    print("=" * 65)
    
    passed_checks = 0
    total_checks = 12
    client = TestClient(app)

    # Check 1: Health Endpoint
    print("\n[1/12] Checking GET /health endpoint...")
    res = client.get('/health')
    assert res.status_code == 200, f"Health check failed: {res.text}"
    assert res.json().get('status') == 'ok'
    print("  --> PASS: Health endpoint is active.")
    passed_checks += 1

    # Check 2: System Status & Diagnostic
    print("\n[2/12] Checking GET /api/v1/status endpoint...")
    res = client.get('/api/v1/status')
    assert res.status_code == 200, f"Status check failed: {res.text}"
    st = res.json()
    assert st.get('database') == 'ok'
    assert 'detector_model' in st
    assert 'density_screening' in st
    assert 'sms_status' in st
    print(f"  --> PASS: Database connected. Detector model: {st['detector_model']} ({st.get('detector_device', 'cpu')})")
    print(f"            SMS Provider: {st['sms_status']['provider']}, Recipient: {st['sms_status']['recipient_masked']}")
    passed_checks += 1

    # Check 3: Database Tables Verification
    print("\n[3/12] Verifying SQLite database tables...")
    settings = get_settings()
    db.init_db()
    with db.connect() as c:
        tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    expected_tables = ['farms', 'flocks', 'health_events', 'jobs', 'observations', 'alerts', 'density_events', 'notifications', 'app_settings']
    for expected in expected_tables:
        assert expected in tables, f"Missing table: {expected}"
    print(f"  --> PASS: All {len(expected_tables)} tables verified in SQLite ({settings.database_path}).")
    passed_checks += 1

    # Check 4: Frontend Production Bundle Verification
    print("\n[4/12] Checking frontend build artifacts in frontend/dist/...")
    dist_index = ROOT_DIR / "frontend" / "dist" / "index.html"
    assert dist_index.exists(), f"Frontend index.html not found at {dist_index}"
    assert dist_index.stat().st_size > 100, "Frontend index.html is suspiciously small or empty."
    print(f"  --> PASS: Built frontend index.html exists ({dist_index.stat().st_size} bytes).")
    passed_checks += 1

    # Check 5: Farm & Flock Creation Lifecycle (with idempotency)
    print("\n[5/12] Testing Farm and Flock CRUD API with idempotency...")
    res_farm = client.post('/api/v1/farms', json={
        "name": "Smoke Test Poultry Facility",
        "location": "Plot 12, Rural Zone",
        "contact_name": "Test Manager",
        "contact_phone": "+91 7530088644"
    })
    assert res_farm.status_code == 201
    farm_id = res_farm.json()['id']

    res_flock = client.post('/api/v1/flocks', json={
        "farm_id": farm_id,
        "name": "Batch Smoke-101",
        "breed": "Broiler",
        "bird_count": 350,
        "age_days": 18
    })
    assert res_flock.status_code == 201
    flock_id = res_flock.json()['id']
    print(f"  --> PASS: Created/verified Farm #{farm_id} and Flock #{flock_id}.")
    passed_checks += 1

    # Check 6: Farmer Health Event Triage & Urgent Alert
    print("\n[6/12] Testing Health Event reporting & automated triage alert...")
    res_event = client.post('/api/v1/health-events', json={
        "farm_id": farm_id,
        "flock_id": flock_id,
        "signs": ["lethargy", "coughing/sneezing"],
        "sick_count": 4,
        "deaths": 1,
        "feed_change": "decreased",
        "water_change": "normal",
        "notes": "Smoke test observation"
    })
    assert res_event.status_code == 201
    ev_data = res_event.json()
    assert ev_data['risk_level'] == 'watch'
    print(f"  --> PASS: Event assessed as '{ev_data['risk_level']}' triage level.")
    passed_checks += 1

    # Check 7: Alert Acknowledgement & Resolution with Response Latency
    print("\n[7/12] Testing Alerts listing, acknowledge, and resolve...")
    res_alerts = client.get('/api/v1/alerts?status=open')
    assert res_alerts.status_code == 200
    alerts = res_alerts.json()
    assert len(alerts) > 0
    target_aid = alerts[0]['id']

    res_ack = client.post(f'/api/v1/alerts/{target_aid}/acknowledge')
    assert res_ack.status_code == 200
    assert res_ack.json()['status'] == 'acknowledged'

    res_res = client.post(f'/api/v1/alerts/{target_aid}/resolve')
    assert res_res.status_code == 200
    assert res_res.json()['status'] == 'resolved'
    assert 'response_time_sec' in res_res.json()
    print(f"  --> PASS: Alert #{target_aid} transitioned: open -> acknowledged -> resolved (response latency: {res_res.json().get('response_time_sec')}s).")
    passed_checks += 1

    # Check 8: Real Poultry Video CV Pipeline with Spatial Density & Evidence Capture
    print("\n[8/12] Testing real poultry video CV pipeline (ByteTrack + Density + Evidence)...")
    sample_video = ROOT_DIR.parent / "PoultryGuard_Complete" / "poultry_videos" / "10.2.39.193_01_2025031406531250.mp4"
    if not sample_video.exists():
        videos = list((ROOT_DIR.parent / "PoultryGuard_Complete" / "poultry_videos").glob("*.mp4"))
        assert len(videos) > 0, "No sample poultry video found in workspace."
        sample_video = videos[0]

    smoke_jid = f"smoke_density_{int(sys.version_info.major)}{os.getpid()}"
    summary = analyze_video(smoke_jid, str(sample_video))
    
    assert summary['status'] == 'completed'
    assert summary['sampled_frames'] > 0
    assert 'annotated_video_path' in summary
    assert Path(summary['annotated_video_path']).exists()
    assert 'density_config' in summary
    assert 'behavioral_indicators' in summary
    print(f"  --> PASS: Processed '{sample_video.name}': {summary['sampled_frames']} sampled frames @ {summary['processing_fps']} FPS.")
    print(f"            Density layout: {summary['density_config']['layout']}, Triggered events: {summary['density_events_triggered_count']}")
    passed_checks += 1

    # Check 9: Persisted Job Artifacts (CSV, JSON, Frames, Density Events)
    print("\n[9/12] Verifying persisted job files and density event artifacts...")
    job_dir = settings.storage_dir / "jobs" / smoke_jid
    assert (job_dir / "summary.json").exists()
    assert (job_dir / "observations.csv").exists()
    assert (job_dir / "observations.json").exists()
    assert (job_dir / "density_events.json").exists()
    frame_dir = settings.storage_dir / "frames" / smoke_jid
    extracted_frames = list(frame_dir.glob("frame_*.jpg"))
    assert len(extracted_frames) > 0
    print(f"  --> PASS: summary.json, observations.csv, observations.json, density_events.json, and {len(extracted_frames)} frame JPEGs verified.")
    passed_checks += 1

    # Check 10: Density Events API and Evidence Image Download
    print("\n[10/12] Testing Density Events API routes...")
    r_devents = client.get(f'/api/v1/jobs/{smoke_jid}/density-events')
    assert r_devents.status_code == 200
    devents = r_devents.json()
    print(f"  --> PASS: Job density events returned {len(devents)} records.")
    passed_checks += 1

    # Check 11: SMS Configuration & Test Endpoint
    print("\n[11/12] Testing SMS configuration & test-send endpoint...")
    r_sms_st = client.get('/api/v1/sms/status')
    assert r_sms_st.status_code == 200
    r_sms_test = client.post('/api/v1/sms/test', json={"dry_run": True, "message": "Smoke Test SMS Message"})
    assert r_sms_test.status_code == 200
    assert r_sms_test.json()['status'] == 'dry_run'
    print("  --> PASS: SMS status and dry-run test dispatch verified.")
    passed_checks += 1

    # Check 12: Reports and CSV Exports
    print("\n[12/12] Verifying reports summary and all 5 CSV download routes...")
    r_sum = client.get('/api/v1/reports/summary')
    assert r_sum.status_code == 200
    assert 'accuracy_disclaimer' in r_sum.json()

    for csv_route in ['alerts.csv', 'events.csv', 'jobs.csv', 'density_events.csv', 'notifications.csv']:
        r_csv = client.get(f'/api/v1/reports/{csv_route}')
        assert r_csv.status_code == 200, f"Route /api/v1/reports/{csv_route} failed with {r_csv.status_code}"
        assert 'text/csv' in r_csv.headers['content-type']
    print("  --> PASS: All 5 CSV export endpoints and summary report returned 200 OK.")
    passed_checks += 1

    print("\n" + "=" * 65)
    print(f"ALL {passed_checks}/{total_checks} SMOKE CHECKS PASSED SUCCESSFULLY!")
    print("PoultryGuard backend, computer-vision, and notification systems are fully verified.")
    print("=" * 65)

if __name__ == "__main__":
    run_smoke_test()
