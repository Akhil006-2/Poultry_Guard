# PoultryGuard REST API Specification & Developer Guide

**Base URL**: `http://127.0.0.1:8000`  
**Interactive Swagger UI**: `http://127.0.0.1:8000/docs`  
**ReDoc Documentation**: `http://127.0.0.1:8000/redoc`  

---

## 1. System Endpoints

### `GET /health`
Returns service liveness status.
```json
{
  "status": "ok",
  "service": "PoultryGuard",
  "timestamp": 1776209500.12
}
```

### `GET /api/v1/status`
Returns database connectivity, active neural network detector, compute device (CPU/GPU), and operational parameters.
```json
{
  "api": "ok",
  "database": "ok",
  "detector_model": "yolov8s.pt",
  "detector_device": "cpu",
  "is_custom_model": false,
  "detection_scope": "Generic COCO bird proxy (detections are screening indicators, not confirmed headcounts)",
  "frame_stride": 3,
  "detection_confidence_threshold": 0.1,
  "max_upload_mb": 500,
  "note": "Alerts and detections are screening guidance for human review, not veterinary diagnosis."
}
```

---

## 2. Farm Management (`/api/v1/farms`)

### `POST /api/v1/farms`
Create a new poultry farm record.
- **Request Body**:
  ```json
  {
    "name": "Sunrise Poultry Coop",
    "location": "Sector 4, Greenfield",
    "contact_name": "Rahim Khan",
    "contact_phone": "+91 9876543210",
    "notes": "Smallholder broilers facility"
  }
  ```
- **Response**: `201 Created` with created farm record.

### `GET /api/v1/farms`
List all registered farms with their respective flock counts.

### `GET /api/v1/farms/{id}`
Retrieve a specific farm by ID, including its associated flock batches.

### `PATCH /api/v1/farms/{id}`
Update farm fields.

### `DELETE /api/v1/farms/{id}`
Delete a farm record.

---

## 3. Flock Management (`/api/v1/flocks`)

### `POST /api/v1/flocks`
Register a new flock batch linked to a farm.
- **Request Body**:
  ```json
  {
    "farm_id": 1,
    "name": "Broiler Batch A-04",
    "breed": "Cobb 500",
    "bird_count": 450,
    "age_days": 21,
    "housing_type": "Deep litter coop",
    "status": "active"
  }
  ```

### `GET /api/v1/flocks?farm_id={optional}`
List flock batches with optional farm filtering.

### `GET /api/v1/flocks/{id}`
Retrieve flock details, recent health events, and recent video jobs.

### `PATCH /api/v1/flocks/{id}`
Update flock details (headcount, age, housing).

---

## 4. Video Analysis & Tracking (`/api/v1/videos` & `/api/v1/jobs`)

### `POST /api/v1/videos`
Upload a poultry-house video clip for asynchronous background tracking and behavioral analysis.
- **Content-Type**: `multipart/form-data`
- **Fields**:
  - `file`: MP4, AVI, MOV, MKV, or M4V video binary.
  - `farm_id` (optional integer)
  - `flock_id` (optional integer)
- **Response**: `202 Accepted`
  ```json
  {
    "id": "e418af0a4f0d483eba83ab41ced49534",
    "job_id": "e418af0a4f0d483eba83ab41ced49534",
    "status": "queued",
    "original_name": "coop_camera_01.mp4",
    "bytes": 2450120,
    "status_url": "/api/v1/jobs/e418af0a4f0d483eba83ab41ced49534"
  }
  ```

### `GET /api/v1/jobs`
List all recent analysis jobs, statuses, and summary results.

### `GET /api/v1/jobs/{id}`
Retrieve full job status, processing progress percentage, and summary telemetry.

### `GET /api/v1/jobs/{id}/observations`
Returns frame-by-frame observations JSON array containing timestamp, detection count, persistent track IDs, bounding boxes, motion ratio, and density score.

### `GET /api/v1/jobs/{id}/observations.csv`
Download per-frame time-series data as CSV.

### `GET /api/v1/jobs/{id}/summary`
Retrieve complete summary telemetry JSON for the job.

### `GET /api/v1/jobs/{id}/video`
Stream or download the rendered `annotated.mp4` with bounding boxes, tracking labels, and header overlay.

### `GET /api/v1/jobs/{id}/frames`
List all extracted raw sampled frame filenames for gallery scrub.

### `GET /api/v1/jobs/{id}/frames/{frame_name}`
Download a specific high-resolution sampled frame JPEG.

---

## 5. Health Events & Triage (`/api/v1/health-events`)

### `POST /api/v1/health-events`
Submit farmer observation logs. Evaluates triage risk rules and automatically generates an alert if risk exceeds routine.
- **Request Body**:
  ```json
  {
    "farm_id": 1,
    "flock_id": 1,
    "event_date": "2026-10-15",
    "signs": ["lethargy", "coughing/sneezing"],
    "sick_count": 3,
    "deaths": 1,
    "feed_change": "decreased",
    "water_change": "normal",
    "notes": "Birds resting in corner with ruffled feathers"
  }
  ```
- **Response**: `201 Created`
  ```json
  {
    "id": 12,
    "farm_id": 1,
    "flock_id": 1,
    "risk_level": "watch",
    "advice": "Recheck the flock and water/feed records, isolate visibly sick birds where appropriate, and seek veterinary advice if signs persist or worsen.",
    "is_diagnosis": false
  }
  ```

### `GET /api/v1/health-events`
List past health event reports.

---

## 6. Alerts Center (`/api/v1/alerts`)

### `GET /api/v1/alerts?status={open|acknowledged|resolved}&severity={review|watch|urgent}`
Filter operational alerts.

### `PATCH /api/v1/alerts/{id}`
Update status to `acknowledged` or `resolved`.
```json
{
  "status": "acknowledged"
}
```

### `POST /api/v1/alerts/{id}/acknowledge`
Quick shortcut to acknowledge an open alert.

### `POST /api/v1/alerts/{id}/resolve`
Quick shortcut to resolve an alert (automatically computes and stores response latency in seconds).

---

## 7. Reports & CSV Exports (`/api/v1/reports`)

### `GET /api/v1/reports/summary`
Returns aggregate system telemetry across farms, flocks, events, completed jobs, and average observed detections.

### `GET /api/v1/reports/alerts.csv`
Export all alerts as CSV.

### `GET /api/v1/reports/events.csv`
Export all health events as CSV.

### `GET /api/v1/reports/jobs.csv`
Export video analysis jobs and CV metrics as CSV.
