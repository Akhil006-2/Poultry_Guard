# PoultryGuard Project Inventory & Baseline Assessment

**Date**: 2026-10-15  
**Canonical Workspace Directory**: `C:\Dev\12hr\PoultryGuard_Full`  
**Host Environment**: Windows 11, Python 3.12.10 (also Python 3.13 installed), Node.js v20.x, NVIDIA GeForce RTX 3050 Laptop GPU (4 GB VRAM, Driver 566.07, CUDA 12.7). PyTorch 2.14.1 installed with CPU inference fallback / GPU auto-detection.

---

## 1. Directory & File Inventory

### 1.1 `C:\Dev\12hr` Workspace Structure
| Directory | Role / Origin | Key Contents | Status |
|---|---|---|---|
| `Chicken-Behavior-Analysis` | Original upstream git repository (Tahereh Zarrat Ehsan et al., arXiv:2401.12176, ICCKE 2022 competition) | Notebooks, Darknet source code, YOLOv4 Keras scripts, 20 sample images in `img/`, annotations in `Annotation/`, `yolov8n.pt`, `yolov8s.pt` | Preserved read-only upstream reference |
| `poultry_behaviour_dataset` | Downstream dataset bundle | Subdirectories `job_000004` through `job_000011` with full videos (`job_00000X.mp4`), 400-frame clips (`job_00000X_400frames.mp4`), annotated videos, and `annotations_00000X.json` (tracker/pose keypoints and bbox coordinates) | Preserved dataset resource |
| `PoultryGuard_Backend` | Intermediate backend iteration (Oct 14 23:31) | Early FastAPI backend structure with `app`, `data`, `storage`, `tests` | Superseded by `PoultryGuard_Full` |
| `PoultryGuard_Complete` | Intermediate staging directory (Oct 14 23:34) | Contains `Chicken-Behavior-Analysis`, `PoultryGuard_Backend`, and `poultry_videos/` (21 real poultry house CCTV MP4 files) | Preserved video source |
| `PoultryGuard_Full` | **Canonical Project Directory** (Selected) | Complete FastAPI backend, SQLite database, CV pipeline, test suite, scripts, documentation, and consolidated frontend | **Active canonical target** |
| `venv` | Workspace Python 3.12 virtual environment | Shared packages: torch 2.14.1, ultralytics 8.4.177, opencv-python, fastapi, etc. | Preserved |

---

## 2. Model Files & Checkpoints Verification

1. **`Chicken-Behavior-Analysis/final_training`**:
   - Contains `saved_model.pb`, `keras_metadata.pb`, and `variables/variables.index`.
   - **Verification Finding**: `variables.data-00000-of-00001` is missing. The TensorFlow SavedModel cannot be loaded without variable weights.
2. **`Chicken-Behavior-Analysis/darknet`**:
   - Contains Darknet C source files and configs (`yolov4.cfg`).
   - **Verification Finding**: No Darknet `.weights` binary file is present.
3. **`Chicken-Behavior-Analysis/Annotation`**:
   - `anno3.txt`: 20 lines (each with ~139 dense broiler bounding boxes in YOLO format) for the 20 images in `img/`.
   - `anno4.txt`: 20 lines with sparse bounding boxes.
4. **Ultralytics YOLO Checkpoints**:
   - `yolov8s.pt` (22.5 MB) and `yolov8n.pt` (6.5 MB) exist locally in `PoultryGuard_Full` and `Chicken-Behavior-Analysis`.
   - Verified inspection confirms these are 80-class COCO pretrained models.
   - Class 14 is `bird`. In dense poultry houses with white broilers, COCO `bird` functions as a **generic bird proxy**, not a dedicated broiler detector.
   - In accordance with safety rules, detection outputs using this checkpoint are explicitly tagged as **Bird proxy (unvalidated accuracy)**.

---

## 3. Dataset Images, Videos & Annotations

1. **`poultry_videos`** (21 real MP4 video clips, e.g., `10.2.39.190_*.mp4`, `10.2.39.193_*.mp4`, `20250318_*.mp4`, `20250319_*.mp4`, `20250320_*.mp4`):
   - Dimensions: 640x360 or 1280x720.
   - Frame rates: 10.0 - 25.0 FPS.
   - Durations: 10s to 60s clips showing dense white broiler flocks with feeders, drinkers, and varying occlusion.
2. **`poultry_behaviour_dataset`**:
   - 6 jobs (`job_000004`, `job_000007`, `job_000008`, `job_000009`, `job_000010`, `job_000011`).
   - Each job contains:
     - `annotations_00000X.json`: Contains frame-by-frame tracker bounding boxes (`tracks_bbox`), skeletons, and visible keypoints from an automated assembly pipeline.
     - `job_00000X_400frames.mp4`: Pre-cut 400-frame video segment ideal for fast benchmark and integration testing.

---

## 4. Git Status & Remotes

- `C:\Dev\12hr`: Not a git repository.
- `C:\Dev\12hr\Chicken-Behavior-Analysis`: Git repository on branch `main`, remote `origin: https://github.com/TaherehZarratEhsan/Chicken-Behavior-Analysis.git`. Preserved unmodified.
- `C:\Dev\12hr\PoultryGuard_Full`: Clean local development folder.

---

## 5. Existing Backend APIs & Database Schema

### Database (`data/poultryguard.sqlite3`)
- Tables:
  - `farms`: `id`, `name`, `location`, `created_at`
  - `flocks`: `id`, `farm_id`, `name`, `breed`, `bird_count`, `age_days`, `created_at`
  - `health_events`: `id`, `farm_id`, `flock_id`, `reported_at`, `signs`, `sick_count`, `deaths`, `feed_change`, `water_change`, `notes`, `risk_level`, `status`
  - `jobs`: `id`, `original_name`, `video_path`, `status`, `created_at`, `started_at`, `finished_at`, `error`, `metadata_json`, `result_json`
  - `observations`: `id`, `job_id`, `frame_index`, `timestamp_sec`, `detections`, `track_ids_json`, `boxes_json`, `motion_ratio`, `density_score`
  - `alerts`: `id`, `farm_id`, `flock_id`, `job_id`, `severity`, `title`, `message`, `status`, `created_at`, `acknowledged_at`, `resolved_at`

### Backend Routes in `PoultryGuard_Full`
- System: `GET /health`, `GET /api/v1/status`
- Farms: `POST /api/v1/farms`, `GET /api/v1/farms`
- Flocks: `POST /api/v1/flocks`, `GET /api/v1/flocks`
- Health Events: `POST /api/v1/health-events`, `GET /api/v1/health-events`
- Video Jobs: `POST /api/v1/videos`, `GET /api/v1/jobs`, `GET /api/v1/jobs/{jid}`, `GET /api/v1/jobs/{jid}/observations`, `GET /api/v1/jobs/{jid}/video`, `GET /api/v1/jobs/{jid}/summary`, `GET /api/v1/jobs/{jid}/frames/{frame_name}`
- Alerts: `GET /api/v1/alerts`, `PATCH /api/v1/alerts/{aid}`
- Reports: `GET /api/v1/reports/summary`, `GET /api/v1/reports/alerts.csv`

---

## 6. Frontend Status & Plan

- **Current Status**: No frontend manifest (`package.json`) existed in `C:\Dev\12hr`.
- **Implementation**: Build a clean, responsive single-page web dashboard using React, TypeScript, Vite, Tailwind CSS, Lucide icons, and Recharts under `C:\Dev\12hr\PoultryGuard_Full\frontend`.
- **Capabilities**:
  - Live API integration with `http://127.0.0.1:8000`.
  - Farms and Flocks management with full creation and editing.
  - Video upload with drag-and-drop, real-time polling, frame gallery, observation charts, and HTML5 video playback.
  - Health-event reporting with interactive symptom selection and triage guidance.
  - Alerts center with severity badges, acknowledge and resolve action buttons.
  - Reports export with CSV download and model validation status.
  - Settings screen showing active detector weights, inference device (CPU/GPU), stride, and model limits.
