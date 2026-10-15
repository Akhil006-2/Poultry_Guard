"""PoultryGuard Quantitative Model Evaluation Module

Computes rigorous, repeatable evaluation metrics against manual ground-truth annotations:
- Precision, Recall, F1-Score at IoU >= 0.50
- Mean Average Precision (mAP@0.50 and mAP@0.50:0.95)
- Per-frame count error (MAE, RMSE, Mean Relative Error)
- False positives and false negatives (missed chickens)
- Inference latency and processing FPS

Safety rule: All scores are computed strictly from verified ground-truth labels.
No evaluation metrics are ever fabricated or simulated.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import numpy as np


def compute_box_iou(boxA: List[float], boxB: List[float]) -> float:
    """Computes Intersection over Union (IoU) between two [x1, y1, x2, y2] bounding boxes."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interW = max(0.0, xB - xA)
    interH = max(0.0, yB - yA)
    interArea = interW * interH

    boxAArea = max(0.0, (boxA[2] - boxA[0]) * (boxA[3] - boxA[1]))
    boxBArea = max(0.0, (boxB[2] - boxB[0]) * (boxB[3] - boxB[1]))
    unionArea = boxAArea + boxBArea - interArea

    if unionArea <= 0.0:
        return 0.0
    return interArea / unionArea


def match_boxes_at_iou(
    pred_boxes: List[Dict[str, Any]],
    gt_boxes: List[List[float]],
    iou_threshold: float = 0.50
) -> Tuple[int, int, int, List[Tuple[float, bool]]]:
    """Matches predictions to ground truth boxes greedily by confidence at given IoU threshold.
    Returns: (tp, fp, fn, list of (confidence, is_tp))
    """
    sorted_preds = sorted(pred_boxes, key=lambda b: b.get("confidence", 0.0), reverse=True)
    gt_matched = [False] * len(gt_boxes)
    tp = 0
    fp = 0
    pred_eval: List[Tuple[float, bool]] = []

    for p in sorted_preds:
        p_box = p.get("xyxy", [0, 0, 0, 0])
        conf = float(p.get("confidence", 0.0))
        best_iou = 0.0
        best_gt_idx = -1

        for g_idx, g_box in enumerate(gt_boxes):
            if not gt_matched[g_idx]:
                iou = compute_box_iou(p_box, g_box)
                if iou > best_iou:
                    best_iou = iou
                    best_gt_idx = g_idx

        if best_iou >= iou_threshold and best_gt_idx >= 0:
            gt_matched[best_gt_idx] = True
            tp += 1
            pred_eval.append((conf, True))
        else:
            fp += 1
            pred_eval.append((conf, False))

    fn = len(gt_boxes) - sum(gt_matched)
    return tp, fp, fn, pred_eval


def compute_ap(pred_eval_all: List[Tuple[float, bool]], total_gt: int) -> float:
    """Computes Average Precision (AP) from list of (confidence, is_tp) pairs across all frames."""
    if total_gt == 0:
        return 0.0
    if not pred_eval_all:
        return 0.0

    # Sort all predictions by confidence descending
    sorted_all = sorted(pred_eval_all, key=lambda x: x[0], reverse=True)
    tp_cumsum = 0
    fp_cumsum = 0

    precisions = []
    recalls = []

    for _, is_tp in sorted_all:
        if is_tp:
            tp_cumsum += 1
        else:
            fp_cumsum += 1
        rec = tp_cumsum / float(total_gt)
        prec = tp_cumsum / float(tp_cumsum + fp_cumsum)
        recalls.append(rec)
        precisions.append(prec)

    # 11-point interpolated AP standard
    ap = 0.0
    for r_thresh in np.linspace(0.0, 1.0, 11):
        matching_precs = [p for r, p in zip(recalls, precisions) if r >= r_thresh]
        p_interp = max(matching_precs) if matching_precs else 0.0
        ap += p_interp / 11.0

    return round(float(ap), 4)


def evaluate_detection_dataset(
    detector,
    eval_samples: List[Dict[str, Any]],
    dataset_name: str = "Ground Truth Dataset"
) -> Dict[str, Any]:
    """Evaluates a detector against a list of ground truth image samples.
    
    Each sample dict:
        {
            "image_path": str or Path,
            "gt_boxes": list of [x1, y1, x2, y2],
            "frame_id": str or int
        }
    """
    total_frames = len(eval_samples)
    if total_frames == 0:
        return {
            "status": "error",
            "message": "No evaluation samples provided."
        }

    total_gt_boxes = sum(len(s.get("gt_boxes", [])) for s in eval_samples)
    all_preds_eval_50: List[Tuple[float, bool]] = []
    
    total_tp_50 = 0
    total_fp_50 = 0
    total_fn_50 = 0
    
    count_errors: List[int] = []
    relative_errors: List[float] = []

    start_time = time.time()
    per_frame_records = []

    # Prepare IoU thresholds for mAP@0.50:0.95
    iou_thresholds = [round(float(t), 2) for t in np.linspace(0.50, 0.95, 10)]
    all_preds_eval_by_iou: Dict[float, List[Tuple[float, bool]]] = {t: [] for t in iou_thresholds}

    for s in eval_samples:
        img_path = str(s["image_path"])
        gt_boxes = s.get("gt_boxes", [])
        gt_count = len(gt_boxes)

        import cv2
        img = cv2.imread(img_path)
        if img is None:
            continue

        # Run detector
        pred_boxes = detector.track_frame(img)
        pred_count = len(pred_boxes)

        # Counting error
        err = pred_count - gt_count
        count_errors.append(err)
        rel_err = abs(err) / max(1, gt_count)
        relative_errors.append(rel_err)

        # IoU=0.50 evaluation
        tp, fp, fn, frame_preds = match_boxes_at_iou(pred_boxes, gt_boxes, iou_threshold=0.50)
        total_tp_50 += tp
        total_fp_50 += fp
        total_fn_50 += fn
        all_preds_eval_50.extend(frame_preds)

        # IoU thresholds for mAP@0.50:0.95
        for iou_t in iou_thresholds:
            t_val = round(float(iou_t), 2)
            _, _, _, f_preds_t = match_boxes_at_iou(pred_boxes, gt_boxes, iou_threshold=t_val)
            all_preds_eval_by_iou[t_val].extend(f_preds_t)

        per_frame_records.append({
            "frame_id": s.get("frame_id", Path(img_path).name),
            "ground_truth_count": gt_count,
            "predicted_count": pred_count,
            "count_error": err,
            "tp_50": tp,
            "fp_50": fp,
            "fn_50": fn
        })

    elapsed_time = round(time.time() - start_time, 2)
    eval_fps = round(total_frames / max(0.01, elapsed_time), 2)
    latency_ms = round((elapsed_time / max(1, total_frames)) * 1000.0, 1)

    # Global Metrics at IoU = 0.50
    precision_50 = round(total_tp_50 / max(1, total_tp_50 + total_fp_50), 4)
    recall_50 = round(total_tp_50 / max(1, total_tp_50 + total_fn_50), 4)
    f1_50 = round(
        (2.0 * precision_50 * recall_50) / max(1e-6, precision_50 + recall_50), 4
    ) if (precision_50 + recall_50) > 0 else 0.0

    # mAP@0.50
    map_50 = compute_ap(all_preds_eval_50, total_gt_boxes)

    # mAP@0.50:0.95
    ap_list = []
    for t_val in all_preds_eval_by_iou:
        ap_t = compute_ap(all_preds_eval_by_iou[t_val], total_gt_boxes)
        ap_list.append(ap_t)
    map_50_95 = round(float(np.mean(ap_list)), 4) if ap_list else 0.0

    # Counting Metrics
    count_mae = round(float(np.mean([abs(e) for e in count_errors])), 2) if count_errors else 0.0
    count_rmse = round(float(math.sqrt(np.mean([e**2 for e in count_errors]))), 2) if count_errors else 0.0
    mean_rel_error = round(float(np.mean(relative_errors)) * 100.0, 1) if relative_errors else 0.0

    return {
        "status": "success",
        "dataset_name": dataset_name,
        "model_path": getattr(detector, "model_path", "unknown"),
        "device": getattr(detector, "device", "cpu"),
        "evaluated_frames": total_frames,
        "total_ground_truth_boxes": total_gt_boxes,
        "total_predicted_boxes": sum(p["predicted_count"] for p in per_frame_records),
        "metrics": {
            "precision_50": precision_50,
            "recall_50": recall_50,
            "f1_score_50": f1_50,
            "mAP_50": map_50,
            "mAP_50_95": map_50_95,
            "true_positives_50": total_tp_50,
            "false_positives_50": total_fp_50,
            "false_negatives_missed_chickens_50": total_fn_50,
            "count_mae": count_mae,
            "count_rmse": count_rmse,
            "mean_relative_error_pct": mean_rel_error,
            "processing_time_sec": elapsed_time,
            "inference_latency_ms_per_frame": latency_ms,
            "evaluation_fps": eval_fps
        },
        "per_frame_summary": per_frame_records[:15],
        "validation_statement": (
            "This report documents quantitative detector evaluation against manual ground-truth annotations. "
            "Scores represent actual measurement and confirm whether the active detector is a generic proxy or verified poultry model."
        )
    }
