# PoultryGuard Model Card — YOLOv8s Bird Proxy & Spatial Screening

## 1. Model Details

- **Model Name:** PoultryGuard Baseline Detector (YOLOv8s)
- **Model Architecture:** YOLOv8 Small (`yolov8s.pt`), CNN-based anchor-free object detector with path aggregation network (PAN) and decoupled detection head.
- **Framework:** Ultralytics YOLOv8 (`v8.4.177`) on PyTorch (`v2.14.1+cpu`).
- **Base Checkpoint:** Pretrained weights on Microsoft Common Objects in Context (MS-COCO) 80-class challenge.
- **Active Class Evaluated:** Class index 14 (`bird`).
- **Inference Parameters:** Confidence threshold = 0.10, IoU threshold = 0.45, Image size = 960×960.
- **Tracking Algorithm:** ByteTrack (ByteTrack matching on high- and low-confidence detection boxes).

---

## 2. Intended Use & Application Scope

### Primary Intended Use
PoultryGuard utilizes this detector as a **first-stage visual proxy** to capture relative movement and image-space spatial concentration in smallholder chicken coops.
- Early-warning screening of flock activity patterns.
- Detecting persistent clustering in localized zones (feeders, drinkers, draft areas).
- Tracking centroid movement drift over sampled surveillance clips.

### Out-of-Scope & Prohibited Uses
- **Clinical Disease Diagnosis:** The model detects geometric visual bounding boxes of bird-like forms; it **cannot** detect viral, bacterial, or fungal pathogens (e.g. Avian Influenza, Newcastle Disease, Infectious Bronchitis).
- **Physical Headcount or Legal Census:** Due to severe bird-on-bird occlusion, detections represent visible surface birds, not total biological headcount.
- **Automated Medical Dispensing:** Output should never trigger autonomous medication or feed adulteration without human veterinary review.

---

## 3. Quantitative Evaluation (Ground-Truth Benchmark)

Evaluated against 16 manually annotated ground-truth commercial broiler coop frames containing **1,305 labeled chickens** from `poultry_behaviour_dataset` (`job_000004`) and `anno3.txt`:

| Benchmark Metric | Measured Result | Significance |
| :--- | :---: | :--- |
| **Precision @ IoU=0.50** | **61.62%** | ~61.6% of generated bounding boxes accurately correspond to real chickens. |
| **Recall @ IoU=0.50** | **4.67%** | **Only ~4.7% of total chickens in the coop are detected.** (~95% missed due to occlusion). |
| **F1-Score @ IoU=0.50** | **8.68%** | Harmonic mean highlighting the critical recall limitation. |
| **mAP @ IoU=0.50** | **6.68%** | Mean Average Precision at IoU 0.50. |
| **mAP @ IoU=0.50:0.95** | **2.06%** | Standard COCO multi-threshold average precision. |
| **Count Mean Absolute Error (MAE)** | **75.38 birds** | Average count discrepancy per frame against human ground truth. |
| **Count Root Mean Square Error (RMSE)**| **107.62 birds** | Root mean square count error. |
| **Mean Relative Count Error** | **67.10%** | Average undercounting fraction. |
| **Inference Latency** | **454.4 ms** | Latency per frame on standard CPU. |
| **Processing Throughput** | **2.2 FPS** | Real-world CPU processing speed. |

---

## 4. Known Failure Modes & Limitations

1. **Occlusion in High-Density Floor Housing:** White broilers resting or feeding together blend into a single continuous mass. Standard COCO weights only fire on isolated birds at the perimeter.
2. **Obstruction by Feeder & Drinker Equipment:** Suspended feeding trays and water pipes bisect chicken bodies, causing false negatives or fragmented double boxes.
3. **Plumage and Bedding Camouflage:** In low light or dusty coop conditions, white birds against light rice-husk bedding have indistinct contrast.
4. **Camera Perspective Distortion:** Chickens near the camera appear large while chickens at the rear appear small, skewing pixel-area calculations unless perspective calibration is applied.

---

## 5. Guidelines for Fine-Tuning a Poultry-Specific Model

To achieve high recall (>85%) in commercial coops:
1. Label 500–1,000 frames from your specific coop cameras using tools like CVAT or Roboflow.
2. Train a custom YOLOv8 model:
   ```bash
   yolo detect train data=coop_dataset.yaml model=yolov8s.pt epochs=50 imgsz=960 batch=8
   ```
3. Place the resulting `best.pt` file in `C:\Dev\12hr\PoultryGuard_Full\models\custom_chicken.pt`.
4. Configure `.env`:
   ```ini
   CUSTOM_MODEL_PATH=./models/custom_chicken.pt
   ```
5. Rerun evaluation:
   ```bash
   python scripts/evaluate_model.py
   ```
