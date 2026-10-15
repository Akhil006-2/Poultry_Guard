# PoultryGuard scope and evaluation

## Inputs
- Video from a poultry-house camera
- Farm/flock metadata and location (free-text, not geocoded)
- User-reported signs, sick-bird count, deaths, feed/water changes, notes

## Outputs
- Frame samples and annotated video
- Per-frame predicted detections/confidence, frame motion ratio, box-area fraction
- Persistent jobs, farmer events, alerts and CSV/JSON reports

## Evaluation targets
- Detector: precision, recall, mAP@0.5 and mAP@0.5:0.95 from labeled bounding boxes
- Count: MAE, RMSE and bias against manual frame counts
- Service: upload-to-result time, job failures, alert acknowledgement/resolution time
- Farmer event workflow: completeness of required inputs and response tracking

## Non-goals in this prototype
- No disease diagnosis
- No guaranteed all-chicken detection
- No calibrated physical density or clinical behavior classification
- No production authentication, multi-tenant access control, or durable task queue
