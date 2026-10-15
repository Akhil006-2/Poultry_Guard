# PoultryGuard REST API Reference Guide

All REST API endpoints are prefixed with `/api/v1` and return JSON payloads unless requesting video or image streams.
Interactive Swagger documentation is available at `http://127.0.0.1:8000/docs`.

---

## 1. System & Health

### `GET /health`
Returns service availability status.
```json
{
  "status": "ok",
  "service": "PoultryGuard"
}
```

### `GET /api/v1/status`
Returns runtime system status, database health, active computer vision model, compute device, and SMS engine state.

---

## 2. Farms & Flocks

### `GET /api/v1/farms`
List all registered poultry facilities with flock counts.

### `POST /api/v1/farms`
Register a new farm facility (idempotent on duplicate name).
```json
{
  "name": "Sunrise Organic Poultry",
  "location": "North Ward, Greenfield",
  "contact_name": "Fatima Bi",
  "contact_phone": "7530088644",
  "notes": "Coop A & B broiler house"
}
```

### `GET /api/v1/flocks?farm_id={id}`
List flocks, optionally filtered by farm ID.

### `POST /api/v1/flocks`
Register a new flock batch (idempotent on duplicate name).
```json
{
  "farm_id": 1,
  "name": "Coop 1 Broiler Batch-04",
  "breed": "Cobb 500",
  "bird_count": 500,
  "age_days": 21,
  "housing_type": "Deep litter rice husk"
}
```

---

## 3. Health Events & Field Triage

### `GET /api/v1/health-events`
Retrieve chronological log of farmer-reported health events.

### `POST /api/v1/health-events`
Record a new health observation and calculate triage priority.
```json
{
  "farm_id": 1,
  "flock_id": 1,
  "event_date": "2026-10-15",
  "signs": ["Lethargy", "Reduced movement", "Breathing difficulty"],
  "sick_count": 8,
  "deaths": 2,
  "feed_change": "decreased",
  "water_change": "normal",
  "notes": "Birds clustering in corner; dull feathers."
}
```
**Response:**
```json
{
  "id": 1,
  "risk_level": "urgent",
  "advice": "URGENT ADVISORY: 2 deaths reported with severe respiratory/clinical signs. Isolate affected birds and immediately contact a licensed veterinarian.",
  "is_diagnosis": false
}
```

---

## 4. Video Surveillance & Analytics

### `POST /api/v1/videos`
Upload a surveillance clip for asynchronous computer-vision processing.
- **Form Data:** `file` (MP4/AVI/MOV), `farm_id` (optional), `flock_id` (optional)
- **Response:** `{"id": "job_id", "job_id": "job_id", "status": "queued", "original_name": "clip.mp4"}`

### `GET /api/v1/jobs`
List all video analysis jobs with status, progress, and detection summaries.

### `GET /api/v1/jobs/{job_id}`
Retrieve detailed job record, processing metrics, behavioral indicators, and density distribution.

### `GET /api/v1/jobs/{job_id}/video`
Stream the annotated MP4 video with overlaid bounding boxes, tracking trails, and status banner.

### `GET /api/v1/jobs/{job_id}/frames`
List filenames of all sampled frame JPEGs.

### `GET /api/v1/jobs/{job_id}/frames/{frame_name}`
Download or view a specific high-resolution sampled raw frame.

---

## 5. Spatial High-Density Screening

### `GET /api/v1/density-events?job_id={jid}&farm_id={fid}&review_status={status}`
List spatial high-density clustering events with optional filters.

### `GET /api/v1/jobs/{job_id}/density-events`
List all density events triggered for a specific video job.

### `GET /api/v1/jobs/{job_id}/density-events/{event_id}/image?type=annotated|original`
Download or inspect the captured evidence image:
- `type=annotated`: Includes grid lines, highlighted zone, bounding boxes, labels, and header banner.
- `type=original`: Unmodified raw frame at trigger instant.

### `PATCH /api/v1/density-events/{event_id}`
Update the human review status of a density event.
```json
{
  "review_status": "resolved",
  "notes": "Drinker line adjusted; crowding resolved."
}
```

---

## 6. Review Alerts Center

### `GET /api/v1/alerts?status={status}&severity={severity}&alert_type={type}`
List review alerts with flexible filtering:
- `status`: `open`, `acknowledged`, `resolved`
- `severity`: `urgent`, `watch`, `review`
- `alert_type`: `health_review`, `density_review`, `behavioral_screening`, `system_quality`

### `POST /api/v1/alerts/{alert_id}/acknowledge`
Acknowledge an open alert.

### `POST /api/v1/alerts/{alert_id}/resolve`
Mark an alert resolved with optional resolution summary.
```json
{
  "dismiss_reason": "Flock inspected and drinkers serviced."
}
```

---

## 7. SMS Notification Engine

### `GET /api/v1/sms/status`
Returns active SMS provider, normalized masked recipient, cooldown timer, and readiness.

### `POST /api/v1/sms/test`
Dispatch a test operational SMS.
```json
{
  "dry_run": true,
  "message": "[PoultryGuard TEST] Operational alert verification."
}
```

### `GET /api/v1/sms/notifications`
Retrieve chronological audit log of all notification dispatches.

---

## 8. Quantitative Model Evaluation

### `GET /api/v1/evaluation/results`
Retrieve empirical ground-truth benchmark metrics (Precision, Recall, F1, mAP@0.5, Count MAE/RMSE, Latency).

---

## 9. Reports & CSV Data Exports

Download audit CSV files for external analysis or veterinary records:
- `GET /api/v1/reports/summary`: Aggregate statistics (counts, resolution ratios, mean detections).
- `GET /api/v1/reports/alerts.csv`: Complete alerts history with response latency.
- `GET /api/v1/reports/events.csv`: Farmer field health event logs.
- `GET /api/v1/reports/jobs.csv`: Video surveillance analysis jobs.
- `GET /api/v1/reports/density_events.csv`: Spatial high-density clustering events.
- `GET /api/v1/reports/notifications.csv`: SMS and notification audit records.
