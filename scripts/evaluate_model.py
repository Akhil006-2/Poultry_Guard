"""PoultryGuard Model Accuracy Evaluation Runner

Executes repeatable evaluation of the active detector against ground-truth chicken annotations:
1. Chicken-Behavior-Analysis dataset (anno3.txt + img/ 1080p frames)
2. poultry_behaviour_dataset (annotations_000004.json + video frames)

Saves results to data/model_evaluation.json and displays complete metrics.
"""
import sys
import os
import json
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import cv2
from app.analysis import get_detector
from app.evaluation import evaluate_detection_dataset


def load_cba_ground_truth(limit: int = 10) -> list:
    """Loads ground-truth bounding boxes from Chicken-Behavior-Analysis anno3.txt."""
    cba_base = ROOT_DIR.parent / "Chicken-Behavior-Analysis"
    anno_file = cba_base / "Annotation" / "anno3.txt"
    img_dir = cba_base / "img"

    if not anno_file.exists() or not img_dir.exists():
        print(f"Notice: Chicken-Behavior-Analysis dataset not found at {cba_base}")
        return []

    samples = []
    with open(anno_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    for line in lines[:limit]:
        parts = line.split()
        img_name = parts[0]
        img_path = img_dir / img_name
        if not img_path.exists():
            continue

        gt_boxes = []
        for box_str in parts[1:]:
            coords = [float(v) for v in box_str.split(",")[:4]]
            if len(coords) == 4 and coords[2] > coords[0] and coords[3] > coords[1]:
                gt_boxes.append(coords)

        if gt_boxes:
            samples.append({
                "image_path": str(img_path),
                "gt_boxes": gt_boxes,
                "frame_id": img_name
            })

    return samples


def load_pbd_ground_truth(limit: int = 15) -> list:
    """Extracts ground-truth frames from poultry_behaviour_dataset job_000004."""
    pbd_job = ROOT_DIR.parent / "poultry_behaviour_dataset" / "poultry_behaviour_dataset" / "chickens" / "job_000004"
    anno_file = pbd_job / "annotations_000004.json"
    video_file = pbd_job / "job_000004_400frames.mp4"
    if not video_file.exists():
        video_file = pbd_job / "job_000004.mp4"

    if not anno_file.exists() or not video_file.exists():
        print(f"Notice: poultry_behaviour_dataset job_000004 not found at {pbd_job}")
        return []

    with open(anno_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    frames_data = data.get("frames", [])
    if not frames_data:
        return []

    cache_dir = ROOT_DIR / "data" / "eval_frames_pbd"
    cache_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(video_file))
    if not cap.isOpened():
        return []

    step = max(1, len(frames_data) // limit)
    selected_indices = list(range(0, len(frames_data), step))[:limit]

    samples = []
    for f_idx in selected_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
        ok, frame = cap.read()
        if not ok:
            continue

        frame_data = frames_data[f_idx]
        tracks_bbox = frame_data.get("tracks_bbox", [])
        gt_boxes = []
        for row in tracks_bbox:
            if len(row) >= 4:
                x1, y1, x2, y2 = [float(v) for v in row[:4]]
                if x2 > x1 and y2 > y1:
                    gt_boxes.append([x1, y1, x2, y2])

        if gt_boxes:
            frame_path = cache_dir / f"pbd_frame_{f_idx:05d}.jpg"
            cv2.imwrite(str(frame_path), frame)
            samples.append({
                "image_path": str(frame_path),
                "gt_boxes": gt_boxes,
                "frame_id": f"pbd_job4_f{f_idx}"
            })

    cap.release()
    return samples


def main():
    print("=" * 65)
    print("POULTRYGUARD QUANTITATIVE MODEL ACCURACY EVALUATION")
    print("=" * 65)

    detector = get_detector()
    print(f"Active Detector: {detector.model_path}")
    print(f"Device:          {detector.device}")
    print(f"Settings Conf:   {detector.settings.detect_conf}")
    print("-" * 65)

    # 1. Evaluate on CBA High-Density Poultry Frames
    cba_samples = load_cba_ground_truth(limit=8)
    pbd_samples = load_pbd_ground_truth(limit=8)
    all_samples = cba_samples + pbd_samples

    if not all_samples:
        print("ERROR: No ground truth evaluation samples could be loaded.")
        sys.exit(1)

    print(f"Loaded {len(all_samples)} ground truth frames across 2 datasets:")
    print(f" - Chicken-Behavior-Analysis: {len(cba_samples)} frames")
    print(f" - poultry_behaviour_dataset:  {len(pbd_samples)} frames")
    print("Executing evaluation pipeline...")

    eval_results = evaluate_detection_dataset(
        detector=detector,
        eval_samples=all_samples,
        dataset_name="Aggregated Ground Truth (CBA + Poultry Behavior Dataset)"
    )

    metrics = eval_results["metrics"]
    print("\n" + "=" * 65)
    print("QUANTITATIVE EVALUATION RESULTS")
    print("=" * 65)
    print(f"Evaluated Frames:             {eval_results['evaluated_frames']}")
    print(f"Total Ground Truth Chickens:  {eval_results['total_ground_truth_boxes']}")
    print(f"Total Detected Chickens:      {eval_results['total_predicted_boxes']}")
    print(f"True Positives (IoU >= 0.50): {metrics['true_positives_50']}")
    print(f"False Positives:              {metrics['false_positives_50']}")
    print(f"Missed Chickens (FN):         {metrics['false_negatives_missed_chickens_50']}")
    print("-" * 65)
    print(f"Precision @ 0.50:             {metrics['precision_50'] * 100:.2f}%")
    print(f"Recall @ 0.50:                {metrics['recall_50'] * 100:.2f}%")
    print(f"F1 Score @ 0.50:              {metrics['f1_score_50'] * 100:.2f}%")
    print(f"mAP @ 0.50:                   {metrics['mAP_50'] * 100:.2f}%")
    print(f"mAP @ 0.50:0.95:              {metrics['mAP_50_95'] * 100:.2f}%")
    print(f"Per-Frame Count Error (MAE):  {metrics['count_mae']} birds")
    print(f"Count RMSE:                   {metrics['count_rmse']} birds")
    print(f"Mean Relative Error:          {metrics['mean_relative_error_pct']:.1f}%")
    print("-" * 65)
    print(f"Inference Latency:            {metrics['inference_latency_ms_per_frame']} ms/frame")
    print(f"Processing Speed:             {metrics['evaluation_fps']} FPS")
    print("=" * 65)

    # Persist results to JSON
    out_json = ROOT_DIR / "data" / "model_evaluation.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(eval_results, f, indent=2)

    print(f"\nPersisted evaluation record to: {out_json}")


if __name__ == "__main__":
    main()
