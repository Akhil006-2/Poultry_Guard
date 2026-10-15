# PoultryGuard System Architecture & Technical Specification

## 1. Architectural Overview

PoultryGuard is architected as an edge-ready, local-first decision support application for smallholder poultry management. The system operates on standard CPU hardware or edge GPUs without mandatory cloud dependencies, ensuring data privacy and operational continuity in rural and low-connectivity environments.

```
+-----------------------------------------------------------------------------------+
|                            REACT 19 SINGLE-PAGE CLIENT                            |
|  Dashboard | Farms & Flocks | Video Surveillance | Health Events | Alerts Center  |
|                         Reports & CSV | Settings & Model                          |
+-----------------------------------------------------------------------------------+
                                          | HTTP REST / Static Asset Serving
                                          v
+-----------------------------------------------------------------------------------+
|                                FASTAPI BACKEND                                     |
|  - API Router & Endpoints                                                         |
|  - Idempotent Entity Controllers (Farms, Flocks, Health Events, Alerts)           |
|  - CSV Export Generators & Evidence Image Streaming Handlers                      |
+-----------------------------------------------------------------------------------+
      |                       |                       |                      |
      v                       v                       v                      v
+------------+       +------------------+    +------------------+    +---------------+
| SQLITE WAL |       | COMPUTER VISION  |    | SPATIAL DENSITY  |    | SMS DISPATCH  |
|  DATABASE  |       |     PIPELINE     |    |    SCREENING     |    |    ENGINE     |
|            |       |                  |    |                  |    |               |
| 9 Tables:  |       | - YOLOv8s PyTorch|    | - 2x2, 3x3, 4x4  |    | - Indian GW   |
| farms      |       | - ByteTrack MOT  |    | - Center mapping |    | - Twilio      |
| flocks     |       | - Centroid Speed |    | - Occupied Area  |    | - Mock / Dry  |
| health_ev  |       | - Lethargy Ratio |    | - Persistence    |    | - E.164 Clean |
| jobs       |       | - Baseline Drift |    | - Hysteresis     |    | - Cooldown    |
| observat.  |       | - Coverage Drop  |    | - Evidence Frame |    | - Audit Log   |
| alerts     |       +------------------+    +------------------+    +---------------+
| density_ev |                 |                       |                     |
| notifs     |                 +-----------------------+---------------------+
| app_sett.  |                                         |
+------------+                                         v
                                         +--------------------------+
                                         |     STORAGE ARTIFACTS    |
                                         | - Annotated MP4 Videos   |
                                         | - Sampled Frame JPEGs    |
                                         | - Density Evidence JPEGs |
                                         | - Summary JSON / CSVs    |
                                         +--------------------------+
```

---

## 2. Core Subsystems & Components

### 2.1 Backend Core (`app/main.py`)
- **FastAPI Framework:** Implements asynchronous HTTP handlers with Pydantic request/response validation.
- **Static Mounting:** Mounts `frontend/dist` at the application root (`/`) for self-contained single-executable or local desktop deployments.
- **Job Background Worker:** Runs compute-intensive video processing in background execution threads, preventing HTTP socket timeouts.
- **Idempotent Upsert Controllers:** Prevents duplicate constraint crashes during form submissions.

### 2.2 Database & Concurrency Layer (`app/db.py`)
- **Engine:** SQLite 3.
- **Concurrency Mode:** Write-Ahead Logging (`PRAGMA journal_mode=WAL`).
- **Lock Management:** Configures `PRAGMA busy_timeout = 10000` to prevent database locks during concurrent reads and background job writes.
- **Normalized Schema (9 Tables):**
  1. `farms`: Facility metadata, location, contact information.
  2. `flocks`: Flock batches, breed, declared headcount, age, housing.
  3. `health_events`: Farmer field clinical observations, symptoms, mortality.
  4. `jobs`: Video processing job metadata, progress, and performance metrics.
  5. `observations`: Frame-by-frame detector output, track IDs, motion indices.
  6. `alerts`: Actionable review alerts with severity, lifecycle status, response time.
  7. `density_events`: High-density spatial clustering events with zone assignments.
  8. `notifications`: Audit trail of all SMS and external dispatch events.
  9. `app_settings`: Runtime configurable system and screening parameters.

### 2.3 Computer Vision Pipeline (`app/detector.py`, `app/tracker.py`, `app/video.py`)
- **Detector:** Ultralytics YOLOv8s operating on PyTorch.
- **Tracking Algorithm:** Multi-object tracking (ByteTrack) matching detections across sampled frames to maintain continuous bird identities.
- **Sampling Controller:** Configurable frame stride (samples every Nth frame) balancing CPU processing latency with tracking continuity.

### 2.4 Spatial High-Density Screening Engine (`app/density.py`)
- **Dynamic Partitioning:** Divides frame into 2×2, 3×3, or 4×4 coordinate zones.
- **Centroid Assignment:** Projects bounding-box center coordinates `((x1+x2)/2, (y1+y2)/2)` into zone bounds.
- **Area Coverage:** Computes intersection of detection boxes with zone coordinates to estimate occupied area percentage.
- **Persistence & Hysteresis:** Requires high-density condition to persist across configurable consecutive frames before triggering; clears only when count drops below clearing threshold.
- **Automated Evidence Capture:** Generates `<event_id>_original.jpg` and `<event_id>_annotated.jpg` with high-contrast zone boundaries and top metadata banner.

### 2.5 Behavioral Screening Engine (`app/behavior.py`)
- **Velocity Tracker:** Computes centroid Euclidean displacement between consecutive frames.
- **Lethargy Screening:** Identifies stationary birds ($<5.0\text{ px/s}$) and computes stationary bird ratio.
- **Baseline Motion Drift:** Measures percentage change in motion between early and late surveillance windows.
- **Quality & Coverage Uncertainty:** Monitors sudden drop-offs ($>70\%$ decline) and camera failure frames.

### 2.6 SMS Notification Engine (`app/sms.py`)
- **Provider Abstraction:** Implements `SMSProvider` base interface with concrete providers: `DisabledSMSProvider`, `MockSMSProvider`, `IndianGatewaySMSProvider`, `TwilioSMSProvider`.
- **E.164 Normalization:** Automatically cleans and formats Indian numbers (`7530088644` -> `+917530088644`).
- **Cooldown Rate Limiting:** Prevents duplicate notifications within 300 seconds.
- **Privacy & Security:** Masks phone numbers in frontend bundles and logs (`+91 75300 ****44`).

---

## 3. Storage Hierarchy
```
C:\Dev\12hr\PoultryGuard_Full\
├── data/
│   ├── poultryguard.sqlite3      # SQLite database in WAL mode
│   └── model_evaluation.json     # Cached ground-truth benchmark results
└── storage/
    └── jobs/
        └── <job_id>/
            ├── input.mp4                 # Uploaded video source
            ├── annotated.mp4             # Output MP4 with detection boxes and trails
            ├── summary.json              # Aggregate CV and behavioral metrics
            ├── observations.json         # Frame-level detections
            ├── observations.csv          # Exportable frame observations
            ├── density_events.json       # Triggered spatial clustering events
            ├── frames/                   # Sampled frame JPEGs
            └── density_events/           # Evidence frames (original & annotated)
```
