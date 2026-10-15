# PoultryGuard — Early Warning, Spatial Density & Behavioral Screening System

> **Problem Statement:** Smallholder poultry rearers face sudden flock losses because early behavioral indicators of contagious disease are missed in unmonitored coops.

PoultryGuard is a complete, local-first monitoring application designed specifically for smallholder broiler operations. It connects real-time computer-vision video analytics (YOLOv8 + ByteTrack multi-object tracking) with spatial high-density screening, quantitative behavioral lethargy screening, farmer-reported clinical events, automated risk triage, configurable multi-provider SMS alerting, and comprehensive CSV reporting.

---

## Key Features

1. **Computer Vision Surveillance Pipeline**:
   - Automated video decodability and metadata inspection.
   - Configurable frame sampling stride for fast processing on standard CPU or edge GPU hardware.
   - ByteTrack multi-object tracking assigning persistent track IDs across frames.
   - Clean, non-overlapping bounding boxes with concise confidence labels and top status banners.
   - Rendered annotated MP4 generation and sampled frame JPEG gallery.

2. **Spatial High-Density Screening Engine**:
   - Dynamic 2×2 (4 zones), 3×3 (9 zones), and 4×4 (16 zones) grid partitioning.
   - Bounding-box center zone assignment and occupied image area percentage estimation.
   - Persistence hysteresis across consecutive sampled frames and clearing thresholds to eliminate noise.
   - Automated evidence capture generating dual-frame artifacts: `<event_id>_original.jpg` (unmodified raw frame) and `<event_id>_annotated.jpg` (grid lines, highlighted zone overlay, bounding boxes, labels, and metadata banner).
   - Safe, job-scoped API endpoints to stream and download evidence images.

3. **Behavioral Screening Indicators**:
   - Centroid displacement velocity tracking in pixels per second.
   - Stationary bird ratio (lethargy proxy) identifying inactive birds ($<5.0\text{ px/s}$).
   - Activity drift comparing early surveillance baseline with recent observation windows.
   - Camera coverage and uncertainty detection flagging sudden drop-offs ($>70\%$ decline) or zero-detection frames.

4. **Multi-Provider SMS Notification Dispatcher**:
   - Provider abstraction supporting Indian SMS Gateways (Fast2SMS), Twilio, and dry-run modes.
   - Strict E.164 phone normalization for Indian mobile numbers (`7530088644` -> `+917530088644`).
   - Cooldown rate limiting (`SMS_COOLDOWN_SEC=300`) to prevent duplicate notification spam.
   - Privacy-safe masking in UI and logs (`+91 75300 ****44`).
   - Persistent SQLite audit logging in `notifications` table.

5. **Farmer Health Event Reporting & Field Triage**:
   - Structured logging of sick bird counts, mortality, feed reduction, and water intake changes.
   - Interactive multi-select symptom chips (Lethargy, Breathing difficulty, Bloody droppings, etc.).
   - Transparent rule-based triage (`Routine`, `Watch`, `Urgent`) with immediate veterinary referral guidance.

6. **Operational Review Alerts Center**:
   - Automatic alert triggers for elevated mortality, severe symptoms, spatial high-density, or camera coverage drops.
   - Categorized tabs: Health Reviews, Density Reviews, Behavioral Screening, and System Quality.
   - Full lifecycle workflow: `open` -> `acknowledged` -> `resolved` (with resolution notes).
   - Response latency auditing (seconds from creation to resolution).

7. **Interactive Single-Page Web Dashboard**:
   - Built in **React 19**, **TypeScript**, **Vite 8**, and **Lucide-React**.
   - Directly served by FastAPI at `http://127.0.0.1:8000/`.
   - Interactive spatial density heatmap matrix, evidence frame inspection modal, SMS test panel, and HTML5 video playback.

8. **Comprehensive CSV Auditing & Ground-Truth Model Evaluation**:
   - 5 structured CSV downloads: `alerts.csv`, `events.csv`, `jobs.csv`, `density_events.csv`, `notifications.csv`.
   - Transparent quantitative evaluation against 16 ground-truth frames (1,305 chickens) with real precision, recall, mAP, and MAE benchmarks.

---

## Important Detection & Safety Disclaimers

- **Screening Indicator, Not Veterinary Diagnosis:** Behavioral metrics (motion ratio, density score) and triage rules provide decision support for human review. They do not diagnose avian influenza, Newcastle disease, or other clinical pathogens.
- **COCO Bird Proxy Reality:** The default `yolov8s.pt` model uses class 14 (`bird`) as a generic proxy for poultry. Detections represent visible bird-like forms, not confirmed flock headcounts. Occlusion and clustering in dense commercial broiler housing cause the generic proxy to detect ~4.7% of total chickens.
- **Scientific Integrity:** Detection counts must not be represented as an absolute census. PoultryGuard explicitly separates declared flock size from camera-observed counts.

---

## Quick Start (Windows PowerShell)

### 1. Open Project Directory
```powershell
cd C:\Dev\12hr\PoultryGuard_Full
```

### 2. Verify or Create Python Virtual Environment
```powershell
py -3.12 -m venv .venv
```

### 3. Install Backend Dependencies
```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 4. Build the Frontend
```powershell
cd frontend
npm install
npm run build
cd ..
```

### 5. Configure Environment Variables
```powershell
Copy-Item .env.example .env
```
*(Review `.env` to configure SMS provider credentials or keep dry-run mode active).*

### 6. Start the Backend & Integrated Web UI
```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Once started, open your web browser to:
- **Web Application Dashboard**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Interactive Swagger REST API Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Verification & Testing

### 7. Run Automated PyTest Suite (40 Tests)
```powershell
.\.venv\Scripts\python.exe -m pytest -v
```
*(Covers API endpoints, CRUD, triage rules, spatial density grid calculations, persistence hysteresis, evidence frame generation, phone normalization, cooldown logic, Indian SMS gateway dispatch, and CSV downloads).*

### 8. Run End-to-End System Smoke Test (12 Checks)
```powershell
.\.venv\Scripts\python.exe scripts\smoke_test.py
```
*(Executes an automated 12-step audit testing backend health, database tables, frontend build, real video decoding, density event generation, SMS configuration, and all 5 CSV exports).*

### 9. Run Ground-Truth Model Evaluation
```powershell
.\.venv\Scripts\python.exe scripts\evaluate_model.py
```
*(Evaluates `yolov8s.pt` against the ground-truth broiler dataset and updates `data/model_evaluation.json`).*

---

## One-Click Windows Helper Scripts

- **`setup.bat`**: Automatic Python detection, `.venv` setup, dependency installation, and frontend production build.
- **`start.bat`**: Starts the FastAPI server on `http://127.0.0.1:8000/`.
- **`run_tests.bat`**: Executes the 40 PyTest tests and the 12-step system smoke test.

---

## Documentation Index

- [`VALIDATION_REPORT.md`](VALIDATION_REPORT.md) — Comprehensive empirical evaluation report with ground-truth benchmarks, error analysis, real video metrics, and test results.
- [`MODEL_CARD.md`](MODEL_CARD.md) — YOLOv8s model card detailing architecture, class proxy definition, quantitative benchmarks, known failure modes, and fine-tuning instructions.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — Detailed software architecture, component diagrams, database schema (9 tables), and storage hierarchy.
- [`API_GUIDE.md`](API_GUIDE.md) — Complete REST API endpoint reference with parameters and JSON payloads.
- [`SMS_SETUP_GUIDE.md`](SMS_SETUP_GUIDE.md) — Step-by-step configuration for Indian SMS Gateway (Fast2SMS), Twilio, and dry-run modes with phone normalization rules.
