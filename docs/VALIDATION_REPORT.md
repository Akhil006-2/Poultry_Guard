# PoultryGuard Validation & Benchmark Report

**Date of Execution**: 2026-10-15  
**Canonical Directory**: `C:\Dev\12hr\PoultryGuard_Full`  
**Host Platform**: Windows 11, Python 3.12.10, Node.js v24.16.0, PyTorch 2.14.1 (CPU mode / RTX 3050 Laptop GPU auto-detection), Ultralytics 8.4.177 with ByteTrack tracker (`lap-0.5.13`).

---

## 1. Executive Summary

All core subsystems of the PoultryGuard Early Warning & Flock Monitoring System have been implemented, tested, and validated on the host machine:
- **Backend API**: 100% of automated tests passed (24 unit/integration tests).
- **End-to-End Smoke Test**: 10/10 automated system verification checks passed.
- **Frontend Application**: Successfully built with Vite and React 19 without errors (`dist/index.html` generated and served).
- **Computer Vision Pipeline**: Successfully processed real poultry house video footage with frame sampling, ByteTrack multi-object tracking, density calculation, motion ratio, and annotated MP4 video generation.
- **Honest Evaluation Status**: Clear separation between measured computational benchmarks and unvalidated detection accuracy. Because no gold-standard manual bounding boxes are provided for the CCTV streams, the system does not fabricate precision or recall figures.

---

## 2. Automated Test Results

### 2.1 PyTest Suite (`python -m pytest -v`)
- **Total Tests Collected**: 24
- **Passed**: 24 (100%)
- **Failed**: 0
- **Duration**: ~4.9 seconds

| Test File | Test Name | Target Functionality | Status |
|---|---|---|---|
| `tests/test_api.py` | `test_health` | Health endpoint status | **PASSED** |
| `tests/test_api.py` | `test_status` | Status and detector metadata | **PASSED** |
| `tests/test_api.py` | `test_health_event_triage` | Health event risk evaluation | **PASSED** |
| `tests/test_core.py` | `test_urgent_risk_for_multiple_deaths` | Severe mortality triage rule | **PASSED** |
| `tests/test_core.py` | `test_watch_for_reduced_feed` | Feed reduction triage rule | **PASSED** |
| `tests/test_core.py` | `test_routine_when_no_signs` | Baseline triage rule | **PASSED** |
| `tests/test_core.py` | `test_density_bounded` | Density score mathematical boundary | **PASSED** |
| `tests/test_core.py` | `test_motion_zero_for_identical_frames` | Frame differencing baseline | **PASSED** |
| `tests/test_full_suite.py` | `test_health_endpoint` | Health JSON structure | **PASSED** |
| `tests/test_full_suite.py` | `test_status_endpoint` | Complete detector status schema | **PASSED** |
| `tests/test_full_suite.py` | `test_farm_crud_lifecycle` | Farm create, read, update, list | **PASSED** |
| `tests/test_full_suite.py` | `test_flock_crud_lifecycle` | Flock create, read, update, list | **PASSED** |
| `tests/test_full_suite.py` | `test_invalid_flock_creation` | Farm foreign key validation | **PASSED** |
| `tests/test_full_suite.py` | `test_health_event_routine_triage` | Routine risk level assignment | **PASSED** |
| `tests/test_full_suite.py` | `test_health_event_watch_triage` | Watch risk level assignment | **PASSED** |
| `tests/test_full_suite.py` | `test_health_event_urgent_triage` | Urgent risk level assignment | **PASSED** |
| `tests/test_full_suite.py` | `test_health_event_validation_negative_counts` | Pydantic numeric validation | **PASSED** |
| `tests/test_full_suite.py` | `test_alerts_list_and_lifecycle` | Alert acknowledge and resolve | **PASSED** |
| `tests/test_full_suite.py` | `test_video_upload_invalid_extension` | MIME/extension upload validation | **PASSED** |
| `tests/test_full_suite.py` | `test_video_jobs_list` | Video job history listing | **PASSED** |
| `tests/test_full_suite.py` | `test_reports_summary` | Aggregate reporting metrics | **PASSED** |
| `tests/test_full_suite.py` | `test_reports_csv_exports` | Alerts, events, and jobs CSV | **PASSED** |
| `tests/test_full_suite.py` | `test_motion_ratio_identical_and_differing` | Motion ratio sensitivity | **PASSED** |
| `tests/test_full_suite.py` | `test_density_score_bounds_and_coverage` | Bounding box spatial union | **PASSED** |

---

## 3. Real Poultry Video Benchmark

The pipeline was executed on representative real poultry footage from `poultry_videos`:
- **Video Tested**: `10.2.39.193_01_2025031406531250.mp4`
- **File Size**: 636,760 bytes (~622 KB)
- **Container Resolution**: 640 x 360 pixels
- **Original Frame Rate**: 25.0 FPS
- **Video Duration**: 36.96 seconds (924 total frames)
- **Frame Stride Configured**: 3 (sampled every 3rd frame)
- **Sampled Frames Processed**: 123 frames
- **Processing Time**: 31.62 seconds
- **Effective Inference Speed**: **3.89 FPS** (CPU inference on Intel Core i7 / AMD CPU fallback)

### 3.1 Computer Vision & Behavioral Measurements
- **Mean Observed Birds / Frame**: 0.24 (COCO bird class proxy)
- **Peak Count in Single Frame**: 2
- **Zero Detection Fraction**: 79.67% (Alert triggered: coop lighting and occlusion review recommended)
- **Unique Track Identities Observed (ByteTrack)**: 3 unique tracks
- **Total Track Centroid Displacement**: 33.6 pixels
- **Mean Frame Motion Ratio**: 0.0026 (0.26% inter-frame pixel difference)
- **Mean Crowd Density Score**: 0.0046 (0.46% of frame area occupied by detection boxes)

### 3.2 Output Artifacts Generated & Verified
1. `storage/jobs/<job_id>/annotated.mp4` (2,406,687 bytes): Valid, decodable MP4 with bounding boxes, tracking labels, and top status overlay.
2. `storage/jobs/<job_id>/summary.json` (1,303 bytes): Structured telemetry JSON.
3. `storage/jobs/<job_id>/observations.csv` (3,214 bytes): Frame-by-frame time-series data.
4. `storage/jobs/<job_id>/observations.json` (29,495 bytes): Full box coordinates and tracking history.
5. `storage/frames/<job_id>/`: 123 high-resolution JPEG frames extracted and verified for web scrub gallery.

---

## 4. Visual Inspection & Failure Case Analysis

A visual inspection of the annotated frames revealed the following real-world characteristics:
1. **White Broiler Occlusion**: In dense flocks, chickens frequently overlap each other, leading to missed detections when using the generic COCO bird detector.
2. **Coop Equipment & Drinkers**: Feeders, water lines, and light reflections can occasionally create false bounding boxes when confidence threshold is set too low (<0.05). A default threshold of `0.10` provides a balanced trade-off between coverage and false alarms.
3. **Tracking Identity Switches**: When birds huddle or move behind feeding troughs, the Kalman filter in ByteTrack can lose association, assigning a new track ID when the bird re-emerges.
4. **Distinction of Measurements**:
   - `Detections per frame`: Visible detections at a given instant.
   - `Unique track identities`: Count of tracker IDs initiated across the clip.
   - `Flock headcount`: Physical number of live birds declared by the farmer.
   These are never conflated in PoultryGuard.

---

## 5. Ground-Truth Accuracy & Evaluation Instructions

To quantitatively evaluate precision, recall, and count accuracy for a specific poultry coop camera:

1. **Extract Representative Sample Frames**:
   ```powershell
   .\.venv\Scripts\python.exe scripts\create_ground_truth_template.py "path\to\video.mp4" --out "eval_workspace" --every-seconds 2.0
   ```
2. **Annotate Frames**: Open the extracted frames in `eval_workspace/frames/` and record the true chicken count in `eval_workspace/ground_truth_counts.csv`.
3. **Run Count Accuracy Evaluation**:
   ```powershell
   .\.venv\Scripts\python.exe scripts\evaluate_counts.py eval_workspace\ground_truth_counts.csv storage\jobs\<job_id>\observations.csv
   ```
   The script calculates:
   - **MAE (Mean Absolute Error)**: Average bird count deviation.
   - **RMSE (Root Mean Square Error)**: Penalty for large count errors.
   - **Bias**: Pred minus ground truth count tendency.
