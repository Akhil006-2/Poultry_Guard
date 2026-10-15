# PoultryGuard Architecture & System Design

**Project Name**: PoultryGuard — Early Warning and Flock Monitoring System  
**Version**: 1.1.0  
**Target Environment**: Windows 11 / Windows Server, Python 3.12, Node.js v20+, SQLite 3, NVIDIA RTX 3050 Laptop GPU / CPU fallback.

---

## 1. System Overview

Smallholder poultry farmers face sudden, catastrophic flock mortality when early behavioral, environmental, and clinical indicators of contagious disease (such as Newcastle Disease, Avian Influenza, or Infectious Bronchitis) go undetected in unmonitored or uninstrumented coops.

PoultryGuard provides an integrated, local-first early warning and flock monitoring platform combining:
1. **Computer-Vision Surveillance Analytics**: Multi-object tracking (ByteTrack) on poultry house CCTV streams to monitor visible bird counts, spatial clustering (density proxy), and movement/displacement (activity proxy).
2. **Farmer Self-Reported Health Events**: Structured reporting of symptoms, mortality, and feed/water consumption changes.
3. **Automated Risk Triage**: Deterministic, transparent rule engines that categorize flock health into `Routine`, `Watch`, and `Urgent` tiers.
4. **Actionable Alerts Center**: Escalation tracking with response time auditing and acknowledgement/resolution workflows.
5. **Modern Reactive Web UI**: Interactive dashboard built in React, TypeScript, and Vite with frame galleries, video playback, and CSV data export.

```
+-----------------------------------------------------------------------------------+
|                                  USER / BROWSER                                   |
|                (http://localhost:5173  or  http://127.0.0.1:8000)                 |
+-----------------------------------------------------------------------------------+
                                          |
                      REST API / Static Files / Video Streaming
                                          v
+-----------------------------------------------------------------------------------+
|                               FASTAPI APPLICATION                                 |
|                               (app/main.py :8000)                                 |
|                                                                                   |
|  +-----------------+  +-----------------+  +-----------------+  +---------------+ |
|  | Farms & Flocks  |  | Video Analysis  |  | Health Events   |  | Review Alerts | |
|  | CRUD Endpoints  |  | Upload & Stream |  | Triage Engine   |  | State Machine | |
|  +-----------------+  +-----------------+  +-----------------+  +---------------+ |
+-----------------------------------------------------------------------------------+
         |                        |                                    |
         v                        v                                    v
+-----------------+   +------------------------------------+   +--------------------+
|  SQLITE DB      |   |       COMPUTER VISION PIPELINE     |   | LOCAL FILE STORAGE |
|  (data/poultry  |   |          (app/analysis.py)         |   | (storage/)         |
|   guard.sqlite3)|   |                                    |   |                    |
|                 |   |  - OpenCV Frame Decoding           |   | - uploads/         |
| - farms         |   |  - YOLOv8 (COCO Bird / Custom)     |   | - jobs/<id>/       |
| - flocks        |   |  - ByteTrack Multi-Object Tracker  |   |   * annotated.mp4  |
| - health_events |   |  - Inter-frame Motion Ratio        |   |   * summary.json   |
| - jobs          |   |  - Bounding Box Density Score      |   |   * observations.* |
| - observations  |   |  - Clean Annotation Rendering      |   | - frames/<id>/     |
| - alerts        |   +------------------------------------+   |   * frame_*.jpg    |
+-----------------+                                            +--------------------+
```

---

## 2. Component Design

### 2.1 Backend (`app/`)
- **`app/main.py`**: FastAPI entrypoint hosting REST endpoints for system status, farms, flocks, video jobs, health events, alerts, and reports. Also mounts the pre-built React frontend located at `frontend/dist`.
- **`app/analysis.py`**: Video processing worker. Samples frames at a configurable stride (default: every 3rd frame), passes frames to the detector and ByteTrack tracker, logs centroid trajectories, computes density and motion scores, renders annotated MP4 files, and saves CSV/JSON summaries.
- **`app/risk.py`**: Conservative health-triage evaluation engine. Evaluates clinical symptom combinations, mortality thresholds, and feed/water drops to assign risk levels without making claims of automated veterinary diagnosis.
- **`app/db.py`**: SQLite database connection manager, schema initialization, and safe dynamic column migration.
- **`app/schemas.py`**: Pydantic v2 validation models for request/response bodies.
- **`app/config.py`**: Pydantic-settings management reading `.env` parameters.

### 2.2 Computer Vision Engine
- **Detector**: Ultralytics YOLOv8s / YOLOv8n.
  - If a custom model is supplied via `CUSTOM_MODEL_PATH`, all classes defined by the model are detected.
  - If the default COCO checkpoint is used, class 14 (`bird`) is applied as a proxy for poultry, and detections are clearly marked as `Bird (proxy)`.
- **Tracker**: ByteTrack (`bytetrack.yaml`). Links detections across frames by matching Kalman filter predictions with high- and low-confidence detection boxes, maintaining persistent identity tracks (`track_id`).
- **Activity / Motion Metric**:
  - `motion_ratio`: Absolute pixel difference between consecutive grayscale frames scaled to 320x180, calculating the fraction of non-zero thresholded pixels.
  - `centroid_displacement`: Euclidean distance traveled by tracked bird centroids over time.
- **Crowd Density Proxy**:
  - `density_score`: Union area of all bounding boxes in the frame divided by total frame area, bounded between 0.0 and 1.0.

### 2.3 Frontend (`frontend/`)
- Built with **React 19**, **TypeScript**, and **Vite 8**.
- Iconography provided by **Lucide-React**.
- Single-page application architecture with 7 distinct views:
  1. **Dashboard**: High-level telemetry, flock counts, active alerts, and recent jobs.
  2. **Farms & Flocks**: Registration and management of physical coops and bird batches.
  3. **Video Analysis**: Video upload dropzone, real-time job progress polling, HTML5 video player, metadata telemetry, frame-level observations table, and frame gallery.
  4. **Health Events**: Multi-select symptom chips, mortality inputs, and immediate triage advice banners.
  5. **Alerts Center**: Alert filtering, acknowledgement, and resolution with latency measurement.
  6. **Reports & CSV**: Exportable CSV reports for alerts, health events, and video jobs.
  7. **Settings & Model**: Diagnostic inspect of model paths, device execution mode (CPU/GPU), and storage limits.

---

## 3. Data Storage & Schema Design

Database file: `data/poultryguard.sqlite3`

| Table | Columns | Purpose |
|---|---|---|
| `farms` | `id`, `name`, `location`, `contact_name`, `contact_phone`, `notes`, `created_at`, `updated_at` | Physical farm sites |
| `flocks` | `id`, `farm_id`, `name`, `breed`, `bird_count`, `age_days`, `housing_type`, `status`, `created_at`, `updated_at` | Bird batches |
| `health_events` | `id`, `farm_id`, `flock_id`, `event_date`, `reported_at`, `signs`, `sick_count`, `deaths`, `feed_change`, `water_change`, `notes`, `risk_level`, `status` | Farmer self-reports |
| `jobs` | `id`, `farm_id`, `flock_id`, `original_name`, `video_path`, `status`, `progress_percent`, `created_at`, `started_at`, `finished_at`, `error`, `metadata_json`, `result_json` | Video analysis jobs |
| `observations` | `id`, `job_id`, `frame_index`, `timestamp_sec`, `detections`, `track_ids_json`, `boxes_json`, `motion_ratio`, `density_score` | Per-frame detection records |
| `alerts` | `id`, `farm_id`, `flock_id`, `job_id`, `severity`, `title`, `message`, `status`, `created_at`, `acknowledged_at`, `resolved_at`, `response_time_sec` | Review alerts |

File storage structure:
```
storage/
  uploads/             <-- Safe UUID-named uploaded video files
  jobs/<job_id>/       <-- Job output artifacts
    annotated.mp4      <-- Rendered MP4 with tracking boxes and stats banner
    summary.json       <-- Comprehensive job metrics JSON
    observations.csv   <-- Per-frame time-series CSV
    observations.json  <-- Per-frame time-series JSON
  frames/<job_id>/     <-- Extracted raw sampled frame JPEGs
    frame_00000000.jpg
    frame_00000003.jpg
    ...
```

---

## 4. Operational Safety & Security Guarantees

1. **Path Traversal Protection**: Uploaded files and frame requests are normalized using `Path.name` to prevent directory traversal attacks.
2. **File Size Limits**: Video uploads are streamed in 1 MB chunks and checked against `MAX_UPLOAD_MB` (default 500 MB) to prevent denial-of-service via disk exhaustion.
3. **Decodability Checks**: Video files are verified with OpenCV header probing before queuing analysis jobs.
4. **Non-Blocking Background Tasks**: Heavy neural network video processing runs asynchronously in FastAPI `BackgroundTasks`, keeping API endpoints fully responsive during video inference.
5. **No Hallucinated Accuracy**: The system strictly distinguishes between generic COCO bird proxy detections and verified chicken counts. If no ground-truth annotations exist, the model is reported as `Unvalidated (Proxy Mode)`.
