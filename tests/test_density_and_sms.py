import os
import shutil
import tempfile
from pathlib import Path
import pytest
import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.density import (
    DensityConfig,
    DensityTracker,
    assign_boxes_to_zones,
    get_zone_id,
    get_zone_rect,
    compute_zone_occupied_area_pct,
    compute_density_grid_summary
)
from app.sms import (
    normalize_phone_number,
    mask_phone_number,
    get_sms_provider,
    dispatch_alert_sms,
    format_sms_message,
    DisabledSMSProvider,
    MockSMSProvider
)
from app.behavior import compute_behavioral_indicators
from app.evaluation import compute_box_iou, match_boxes_at_iou, compute_ap
from app import db

client = TestClient(app)

# ---------------------------------------------------------------------------
# 1. Spatial High-Density Screening Unit Tests
# ---------------------------------------------------------------------------

def test_zone_id_and_rect_calculation():
    assert get_zone_id(0, 0) == "A1"
    assert get_zone_id(0, 2) == "A3"
    assert get_zone_id(2, 2) == "C3"

    # 3x3 on 1920x1080
    x1, y1, x2, y2 = get_zone_rect(0, 0, 3, 3, 1920, 1080)
    assert x1 == 0 and y1 == 0
    assert x2 == 640 and y2 == 360

    # 2x2 on 1000x1000
    x1, y1, x2, y2 = get_zone_rect(1, 1, 2, 2, 1000, 1000)
    assert x1 == 500 and y1 == 500
    assert x2 == 1000 and y2 == 1000


def test_assign_boxes_to_zones():
    # 3x3 on 300x300, cell size is 100x100
    boxes = [
        {"xyxy": [10, 10, 30, 30]},    # Center (20, 20) -> row 0, col 0 -> A1
        {"xyxy": [150, 10, 170, 30]},  # Center (160, 20) -> row 0, col 1 -> A2
        {"xyxy": [250, 250, 270, 270]} # Center (260, 260) -> row 2, col 2 -> C3
    ]
    assigned = assign_boxes_to_zones(boxes, 3, 3, 300, 300)
    assert len(assigned["A1"]) == 1
    assert len(assigned["A2"]) == 1
    assert len(assigned["C3"]) == 1
    assert len(assigned["B2"]) == 0


def test_zone_occupied_area_pct():
    zone_rect = (0, 0, 100, 100)
    # No boxes
    assert compute_zone_occupied_area_pct([], zone_rect) == 0.0

    # Box covering roughly 50x50 of the 100x100 zone -> ~25%
    boxes = [{"xyxy": [0, 0, 50, 50]}]
    pct = compute_zone_occupied_area_pct(boxes, zone_rect)
    assert 20.0 <= pct <= 30.0


def test_density_tracker_persistence_and_deduplication():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        config = DensityConfig(
            grid_rows=2,
            grid_cols=2,
            count_threshold=3,
            area_threshold_pct=0.0,  # Only test count condition
            persistence_frames=3,
            clearing_threshold=1,
            clearing_frames=2
        )
        tracker = DensityTracker(config, job_id="test_job", output_dir=temp_dir)
        dummy_frame = np.zeros((400, 400, 3), dtype=np.uint8)

        # Zone A1 is top-left [0..200, 0..200]. Place 3 boxes in A1.
        high_boxes = [
            {"xyxy": [10, 10, 40, 40], "confidence": 0.9, "track_id": 1},
            {"xyxy": [50, 50, 80, 80], "confidence": 0.85, "track_id": 2},
            {"xyxy": [100, 100, 130, 130], "confidence": 0.88, "track_id": 3}
        ]

        # Frame 1: count=3 (persistence=1) -> no event yet
        ev1 = tracker.process_frame(1, 0.1, dummy_frame, high_boxes)
        assert len(ev1) == 0

        # Frame 2: count=3 (persistence=2) -> no event yet
        ev2 = tracker.process_frame(2, 0.2, dummy_frame, high_boxes)
        assert len(ev2) == 0

        # Frame 3: count=3 (persistence=3) -> TRIGGER EVENT!
        ev3 = tracker.process_frame(3, 0.3, dummy_frame, high_boxes)
        assert len(ev3) == 1
        event = ev3[0]
        assert event.zone_id == "A1"
        assert event.detection_count == 3
        assert Path(tracker.output_dir / f"{event.id}_original.jpg").exists()
        assert Path(tracker.output_dir / f"{event.id}_annotated.jpg").exists()

        # Frame 4: count=3 (continuous event) -> DEDUPLICATION: no duplicate event triggered
        ev4 = tracker.process_frame(4, 0.4, dummy_frame, high_boxes)
        assert len(ev4) == 0
        assert tracker.zone_states["A1"]["active_event"].duration_sec >= 0.3

        # Frame 5: count drops to 0 (clearing frame 1)
        ev5 = tracker.process_frame(5, 0.5, dummy_frame, [])
        assert len(ev5) == 0

        # Frame 6: count remains 0 (clearing frame 2) -> Event cleared!
        ev6 = tracker.process_frame(6, 0.6, dummy_frame, [])
        assert len(ev6) == 0
        assert tracker.zone_states["A1"]["active_event"] is None

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_compute_density_grid_summary():
    obs = [
        {"boxes": [{"xyxy": [50, 50, 80, 80]}]},  # In A1
        {"boxes": [{"xyxy": [50, 50, 80, 80]}]},  # In A1
        {"boxes": [{"xyxy": [250, 250, 280, 280]}]}  # In C3
    ]
    summary = compute_density_grid_summary(obs, rows=3, cols=3, width=300, height=300)
    assert summary["grid_layout"] == "3x3"
    assert summary["zone_total_counts"]["A1"] == 2
    assert summary["zone_total_counts"]["C3"] == 1
    assert summary["peak_concentration_zone"] == "A1"


# ---------------------------------------------------------------------------
# 2. SMS Module Unit Tests
# ---------------------------------------------------------------------------

def test_phone_normalization_and_masking():
    # 10 digit Indian number
    valid, norm, err = normalize_phone_number("7530088644")
    assert valid is True
    assert norm == "+917530088644"

    # Already formatted
    valid, norm, err = normalize_phone_number("+917530088644")
    assert valid is True
    assert norm == "+917530088644"

    # Leading 0
    valid, norm, err = normalize_phone_number("07530088644")
    assert valid is True
    assert norm == "+917530088644"

    # Invalid short number
    valid, norm, err = normalize_phone_number("12345")
    assert valid is False

    # Masking
    masked = mask_phone_number("+917530088644")
    assert masked.startswith("+91 75300")
    assert masked.endswith("44")
    assert "****" in masked


def test_disabled_sms_provider():
    provider = DisabledSMSProvider()
    ready, reason = provider.is_configured()
    assert ready is False
    res = provider.send("+917530088644", "Test Alert")
    assert res.success is False
    assert res.status == "not_configured"


def test_mock_sms_provider():
    provider = MockSMSProvider()
    ready, reason = provider.is_configured()
    assert ready is True
    res = provider.send("+917530088644", "Test Alert")
    assert res.success is True
    assert res.status == "sent"
    assert res.provider_message_id is not None


def test_sms_cooldown_and_audit_trail():
    os.environ["SMS_RECIPIENT"] = "7530088644"
    os.environ["SMS_COOLDOWN_SEC"] = "300"
    
    # First dispatch in dry-run
    r1 = dispatch_alert_sms("urgent_health", "PoultryGuard Test Alert 1", force_dry_run=True)
    assert r1.status == "dry_run"
    assert r1.success is True

    # Immediate second dispatch of same category should be cooldown suppressed
    r2 = dispatch_alert_sms("urgent_health", "PoultryGuard Test Alert 2", force_dry_run=False)
    assert r2.status == "cooldown_suppressed"
    assert r2.success is False


# ---------------------------------------------------------------------------
# 3. Behavioral Screening & Indicators Unit Tests
# ---------------------------------------------------------------------------

def test_behavioral_indicators():
    obs = [
        {"frame_index": 0, "timestamp_sec": 0.0, "detections": 10, "motion_ratio": 0.05},
        {"frame_index": 3, "timestamp_sec": 0.2, "detections": 10, "motion_ratio": 0.05},
        {"frame_index": 6, "timestamp_sec": 0.4, "detections": 10, "motion_ratio": 0.04},
        {"frame_index": 9, "timestamp_sec": 0.6, "detections": 10, "motion_ratio": 0.03},
    ]
    # Track 1 moved from (10, 10) to (100, 100) (active)
    # Track 2 stayed at (50, 50) (stationary)
    track_history = {
        1: [(0.0, 10, 10), (0.2, 50, 50), (0.4, 90, 90), (0.6, 100, 100)],
        2: [(0.0, 50, 50), (0.2, 50, 50), (0.4, 50, 50), (0.6, 50, 50)]
    }
    b = compute_behavioral_indicators(obs, track_history, video_fps=15.0, video_duration_sec=0.6)
    assert b["status"] == "computed"
    mv = b["movement_metrics"]
    assert mv["active_birds_count"] == 1
    assert mv["stationary_birds_count"] == 1
    assert mv["stationary_bird_ratio"] == 0.5


# ---------------------------------------------------------------------------
# 4. Quantitative Evaluation Unit Tests
# ---------------------------------------------------------------------------

def test_box_iou_calculation():
    # Exact match
    box = [0, 0, 10, 10]
    assert compute_box_iou(box, box) == 1.0

    # No overlap
    box2 = [20, 20, 30, 30]
    assert compute_box_iou(box, box2) == 0.0

    # Half overlap: box1 [0, 0, 10, 10] area=100, box3 [5, 0, 15, 10] area=100
    # inter [5, 0, 10, 10] area=50, union = 100+100-50=150 -> iou = 50/150 = 1/3
    box3 = [5, 0, 15, 10]
    assert abs(compute_box_iou(box, box3) - (1.0 / 3.0)) < 1e-4


def test_match_boxes_and_ap():
    gt_boxes = [[0, 0, 10, 10], [50, 50, 60, 60]]
    pred_boxes = [
        {"xyxy": [0, 0, 10, 10], "confidence": 0.95},  # True positive
        {"xyxy": [100, 100, 110, 110], "confidence": 0.8} # False positive
    ]
    tp, fp, fn, frame_preds = match_boxes_at_iou(pred_boxes, gt_boxes, iou_threshold=0.5)
    assert tp == 1
    assert fp == 1
    assert fn == 1
    ap = compute_ap(frame_preds, total_gt=2)
    assert ap > 0.0


# ---------------------------------------------------------------------------
# 5. REST API Integration Tests
# ---------------------------------------------------------------------------

def test_density_events_api():
    # Ensure smoke_job exists in jobs table to satisfy foreign key
    db.execute("INSERT OR IGNORE INTO jobs(id, original_name, status) VALUES ('smoke_job', 'test.mp4', 'completed')")

    # Insert a dummy density event directly to test GET and PATCH endpoints
    eid = "de_test_abc123"
    db.execute(
        """INSERT OR REPLACE INTO density_events
           (id, job_id, zone_id, grid_layout, frame_index, timestamp_sec, detection_count, threshold, trigger_reason, review_status)
           VALUES (?, 'smoke_job', 'B2', '3x3', 10, 2.5, 6, 4, 'Test density', 'pending_review')""",
        (eid,)
    )

    # 1. GET /api/v1/density-events
    res = client.get('/api/v1/density-events')
    assert res.status_code == 200
    events = res.json()
    assert any(e['id'] == eid for e in events)

    # 2. PATCH /api/v1/density-events/{eid}
    patch_res = client.patch(f'/api/v1/density-events/{eid}', json={"review_status": "acknowledged", "notes": "Verified by operator"})
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated['review_status'] == 'acknowledged'
    assert updated['notes'] == 'Verified by operator'


def test_sms_api_endpoints():
    # 1. GET /api/v1/sms/status
    res = client.get('/api/v1/sms/status')
    assert res.status_code == 200
    data = res.json()
    assert 'enabled' in data
    assert 'recipient_masked' in data

    # 2. POST /api/v1/sms/test (dry run mode)
    res_test = client.post('/api/v1/sms/test', json={"dry_run": True, "message": "Automated Unit Test SMS"})
    assert res_test.status_code == 200
    test_data = res_test.json()
    assert test_data['status'] == 'dry_run'
    assert test_data['success'] is True

    # 3. GET /api/v1/sms/notifications
    res_notif = client.get('/api/v1/sms/notifications')
    assert res_notif.status_code == 200
    notifs = res_notif.json()
    assert len(notifs) > 0


def test_settings_api_endpoints():
    # 1. GET /api/v1/settings
    res = client.get('/api/v1/settings')
    assert res.status_code == 200
    st = res.json()
    assert 'density' in st
    assert 'sms' in st
    assert 'detection' in st

    # 2. PUT /api/v1/settings/density
    new_density = {
        "grid_rows": 3,
        "grid_cols": 3,
        "count_threshold": 5,
        "area_threshold_pct": 12.5,
        "persistence_frames": 4,
        "clearing_threshold": 2,
        "clearing_frames": 2
    }
    res_put = client.put('/api/v1/settings/density', json=new_density)
    assert res_put.status_code == 200
    assert res_put.json()['density_config']['count_threshold'] == 5


def test_reports_new_csv_endpoints():
    # Test new CSV downloads: density_events.csv, notifications.csv
    r_density = client.get('/api/v1/reports/density_events.csv')
    assert r_density.status_code == 200
    assert 'text/csv' in r_density.headers['content-type']

    r_notif = client.get('/api/v1/reports/notifications.csv')
    assert r_notif.status_code == 200
    assert 'text/csv' in r_notif.headers['content-type']
