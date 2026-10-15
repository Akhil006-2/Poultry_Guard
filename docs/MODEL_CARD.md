# PoultryGuard Model Card

**Model Family**: Ultralytics YOLOv8 (Default: `yolov8s.pt` / `yolov8n.pt`)  
**Pipeline Integration**: Multi-Object Tracking via ByteTrack (`bytetrack.yaml` with `lap-0.5.13`)  
**Input Format**: Video frames decoded by OpenCV (RGB / BGR uint8 arrays)  
**Output Format**: 2D Bounding Boxes `[x1, y1, x2, y2]`, Confidence Score `[0.0 - 1.0]`, Class ID, Class Label, Persistent Track ID  

---

## 1. Intended Use & Target Users

- **Intended Use**: Real-time and batch video screening of smallholder poultry coops. Used to track relative visible bird counts, spatial clustering trends, and approximate movement over time to detect early behavioral disruptions.
- **Target Audience**: Smallholder poultry farmers, cooperative field officers, livestock extension workers, and agricultural monitoring researchers.
- **Out-of-Scope Uses**:
  - Definitive clinical disease diagnosis (e.g. diagnosing Avian Influenza or Newcastle Disease).
  - Automated medication dispensing without veterinary oversight.
  - High-precision legal inventory accounting in commercial industrial processing plants.

---

## 2. Pretraining & Class Mapping

- **Default Checkpoint**: `yolov8s.pt` (22.5 MB) pretrained on the COCO (Common Objects in Context) dataset.
- **Class Filtering**: Class ID 14 (`bird`) is applied as a **generic proxy**.
- **Important Distinction**:
  - Broiler chickens in dense coops possess physical characteristics (compact white feathers, lack of prominent wings/tails when resting, clustering behavior) that diverge from wild birds in COCO.
  - Therefore, detections using the default checkpoint represent **bird-proxy observations** and do not guarantee 100% chicken recall.
  - In all user interfaces and reports, these outputs are explicitly labeled: `Bird (proxy) [COCO Fallback]`.

---

## 3. Factors, Occlusion & Failure Modes

1. **Occlusion in Dense Broilers**: When chickens huddle or overlap, the detector frequently merges multiple adjacent birds into a single box or misses interior birds entirely.
2. **Coop Obstacles**: Feeders, water nipples, PVC piping, and wall perches can cause partial occlusion or false positives if confidence threshold is configured below 0.05.
3. **Lighting & Camera Dust**: Coops often experience low-lux nighttime illumination or dust accumulation on camera lenses, reducing contrast.
4. **Tracking Identity Stability**: ByteTrack utilizes Kalman filters for trajectory association. Rapid movements, huddling, or camera shakes can cause identity reassignment.

---

## 4. Fine-Tuning & Custom Weights

PoultryGuard is designed to be model-agnostic. To deploy a dedicated, poultry-trained detector:

1. Annotate representative frames from your specific farm cameras using standard YOLO format (e.g., with LabelImg, CVAT, or Roboflow).
2. Train a custom YOLOv8 model:
   ```bash
   yolo detect train data=custom_poultry.yaml model=yolov8s.pt epochs=50 imgsz=640
   ```
3. Copy the resulting `best.pt` to the PoultryGuard project folder.
4. Configure in `.env`:
   ```env
   CUSTOM_MODEL_PATH=best.pt
   ```
5. When `CUSTOM_MODEL_PATH` is set, the system automatically uses all custom classes and tags detections as native poultry classes rather than COCO proxies.
