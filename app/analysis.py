"""PoultryGuard Computer Vision Pipeline
Includes ByteTrack tracking, spatial high-density screening (2x2, 3x3, 4x4),
behavioral screening indicators, automated evidence frame generation,
SMS alert dispatching, and frame extraction.
"""
from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Any

import cv2
import numpy as np
import torch

from .config import get_settings
from . import db
from .density import (
    DensityConfig,
    DensityTracker,
    compute_density_grid_summary,
    compute_zone_occupied_area_pct,
    get_zone_id,
    get_zone_rect,
    assign_boxes_to_zones
)
from .behavior import compute_behavioral_indicators
from .sms import dispatch_alert_sms, format_sms_message

_DETECTOR_CACHE = None

class Detector:
    def __init__(self):
        self.settings = get_settings()
        self.model = None
        self.model_error = None
        self.device = "0" if torch.cuda.is_available() else "cpu"
        self.model_path = (self.settings.custom_model_path.strip() 
                           if self.settings.custom_model_path.strip() 
                           else self.settings.model_path)
        
        # Resolve model path relative to project root if local file exists
        local_candidate = Path(self.model_path)
        if not local_candidate.is_absolute() and local_candidate.exists():
            self.model_path = str(local_candidate.resolve())
            
        try:
            from ultralytics import YOLO
            self.model = YOLO(self.model_path)
        except Exception as exc:
            self.model_error = f"Could not load detector '{self.model_path}': {exc}"

    def track_frame(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Track objects across frames using ByteTrack when available, falling back to predict."""
        if self.model is None:
            raise RuntimeError(self.model_error or "Detector unavailable")
        
        is_custom = bool(self.settings.custom_model_path.strip())
        kwargs = {
            "source": frame,
            "conf": self.settings.detect_conf,
            "imgsz": self.settings.image_size,
            "device": self.device,
            "verbose": False
        }
        
        # If default COCO model is used, filter to class 14 (bird) as generic proxy
        if not is_custom and any(self.model_path.lower().endswith(x) for x in ["yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolo11n.pt", "yolo11s.pt"]):
            kwargs["classes"] = [14]
            is_coco_bird = True
        else:
            is_coco_bird = False

        boxes = []
        try:
            # Use ByteTrack multi-object tracker
            results = self.model.track(persist=True, tracker="bytetrack.yaml", **kwargs)
        except Exception:
            # Fallback to standard prediction if tracker encounters any issue
            results = self.model.predict(**kwargs)

        if results and len(results) > 0:
            res = results[0]
            if res.boxes is not None and len(res.boxes) > 0:
                raw_boxes = res.boxes
                xyxy_list = raw_boxes.xyxy.cpu().tolist()
                conf_list = raw_boxes.conf.cpu().tolist()
                cls_list = raw_boxes.cls.cpu().tolist()
                id_list = raw_boxes.id.int().cpu().tolist() if raw_boxes.id is not None else [None] * len(xyxy_list)

                for xyxy, conf, cls_id, track_id in zip(xyxy_list, conf_list, cls_list, id_list):
                    cls_int = int(cls_id)
                    raw_name = res.names.get(cls_int, str(cls_int))
                    display_name = "Bird (proxy)" if is_coco_bird else raw_name
                    boxes.append({
                        "xyxy": [int(v) for v in xyxy],
                        "confidence": round(float(conf), 4),
                        "class_id": cls_int,
                        "class_name": display_name,
                        "track_id": int(track_id) if track_id is not None else None
                    })
        return boxes


def get_detector() -> Detector:
    global _DETECTOR_CACHE
    if _DETECTOR_CACHE is None or _DETECTOR_CACHE.model is None:
        _DETECTOR_CACHE = Detector()
    return _DETECTOR_CACHE


def get_active_density_config() -> DensityConfig:
    """Retrieves the active density configuration from database settings or default."""
    try:
        row = db.one("SELECT value FROM app_settings WHERE key='density_config'")
        if row and row.get("value"):
            data = json.loads(row["value"])
            return DensityConfig(
                grid_rows=int(data.get("grid_rows", 3)),
                grid_cols=int(data.get("grid_cols", 3)),
                count_threshold=int(data.get("count_threshold", 4)),
                area_threshold_pct=float(data.get("area_threshold_pct", 10.0)),
                persistence_frames=int(data.get("persistence_frames", 3)),
                clearing_threshold=int(data.get("clearing_threshold", 2)),
                clearing_frames=int(data.get("clearing_frames", 2)),
                enabled_zones=data.get("enabled_zones")
            )
    except Exception:
        pass
    return DensityConfig(grid_rows=3, grid_cols=3, count_threshold=4, area_threshold_pct=10.0, persistence_frames=3, clearing_threshold=2)


def compute_motion_ratio(prev_gray: Optional[np.ndarray], gray: Optional[np.ndarray]) -> float:
    if prev_gray is None or gray is None:
        return 0.0
    a = cv2.resize(prev_gray, (320, 180))
    b = cv2.resize(gray, (320, 180))
    diff = cv2.absdiff(a, b)
    _, mask = cv2.threshold(diff, 18, 255, cv2.THRESH_BINARY)
    return round(float(np.count_nonzero(mask)) / mask.size, 5)


def compute_density_score(boxes: List[Dict[str, Any]], width: int, height: int) -> float:
    """Estimate image area occupied by detection bounding boxes."""
    if not boxes or width <= 0 or height <= 0:
        return 0.0
    mask_w, mask_h = 320, 180
    scale_x, scale_y = mask_w / float(width), mask_h / float(height)
    mask = np.zeros((mask_h, mask_w), dtype=np.uint8)
    for b in boxes:
        x1, y1, x2, y2 = b["xyxy"]
        mx1 = max(0, min(mask_w, int(x1 * scale_x)))
        my1 = max(0, min(mask_h, int(y1 * scale_y)))
        mx2 = max(0, min(mask_w, int(x2 * scale_x)))
        my2 = max(0, min(mask_h, int(y2 * scale_y)))
        if mx2 > mx1 and my2 > my1:
            mask[my1:my2, mx1:mx2] = 255
    occupied_ratio = float(np.count_nonzero(mask)) / float(mask_w * mask_h)
    return round(occupied_ratio, 5)

motion_ratio = compute_motion_ratio
density_score = compute_density_score


def draw_clean_annotations(
    frame: np.ndarray,
    boxes: List[Dict[str, Any]],
    frame_idx: int,
    count: int,
    unique_tracks_count: int,
    timestamp_sec: float,
    is_coco: bool,
    density_config: Optional[DensityConfig] = None
) -> None:
    """Render legible bounding boxes, subtle grid, and informative summary banner without visual clutter."""
    h, w = frame.shape[:2]

    # Draw subtle grid lines if density config provided
    if density_config:
        for r in range(1, density_config.grid_rows):
            gy = int(round(r * (h / density_config.grid_rows)))
            cv2.line(frame, (0, gy), (w, gy), (80, 100, 110), 1, cv2.LINE_AA)
        for c in range(1, density_config.grid_cols):
            gx = int(round(c * (w / density_config.grid_cols)))
            cv2.line(frame, (gx, 0), (gx, h), (80, 100, 110), 1, cv2.LINE_AA)

    # 1. Draw bounding boxes
    for b in boxes:
        x1, y1, x2, y2 = b["xyxy"]
        tid = b.get("track_id")
        conf = b.get("confidence", 0.0)

        # Color coding: Green for tracked bird, Cyan for untracked
        color = (0, 225, 90) if tid is not None else (255, 200, 0)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        label = f"#{tid} {conf:.2f}" if tid is not None else f"{conf:.2f}"
        (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)

        label_y1 = max(0, y1 - lh - 6)
        label_y2 = y1
        cv2.rectangle(frame, (x1, label_y1), (x1 + lw + 6, label_y2), color, -1)
        cv2.putText(frame, label, (x1 + 3, y1 - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)

    # 2. Semi-transparent top status banner
    banner_height = 44
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, banner_height), (15, 20, 25), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

    proxy_tag = " [COCO Bird Proxy]" if is_coco else ""
    grid_tag = f" | Grid: {density_config.layout_name}" if density_config else ""
    line1 = f"PoultryGuard | Frame {frame_idx} ({timestamp_sec:.1f}s) | Count: {count} | Active Tracks: {unique_tracks_count}{proxy_tag}{grid_tag}"
    cv2.putText(frame, line1, (14, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 255, 255), 2, cv2.LINE_AA)


def analyze_video(job_id: str, video_path: str) -> Dict[str, Any]:
    """Executes full video analysis: tracking, spatial density screening, behavioral statistics,
    frame saving, SMS dispatching, and report generation."""
    settings = get_settings()
    job_dir = settings.storage_dir / "jobs" / job_id
    frames_dir = settings.storage_dir / "frames" / job_id
    density_events_dir = job_dir / "density_events"

    job_dir.mkdir(parents=True, exist_ok=True)
    density_events_dir.mkdir(parents=True, exist_ok=True)
    if settings.save_frames:
        frames_dir.mkdir(parents=True, exist_ok=True)

    detector = get_detector()

    # Retrieve job details and associations
    farm_id = None
    flock_id = None
    farm_name = "Farm"
    flock_name = "Flock"

    with db.connect() as c:
        row = c.execute("SELECT id, farm_id, flock_id FROM jobs WHERE id=?", (job_id,)).fetchone()
        if not row:
            c.execute(
                "INSERT INTO jobs(id, original_name, video_path, status, started_at, progress_percent) VALUES(?,?,?, 'processing', CURRENT_TIMESTAMP, 0.0)",
                (job_id, Path(video_path).name, str(video_path))
            )
        else:
            farm_id = row["farm_id"]
            flock_id = row["flock_id"]
            c.execute("UPDATE jobs SET status='processing', started_at=CURRENT_TIMESTAMP, progress_percent=0.0 WHERE id=?", (job_id,))

        if farm_id:
            f_row = c.execute("SELECT name FROM farms WHERE id=?", (farm_id,)).fetchone()
            if f_row: farm_name = f_row["name"]
        if flock_id:
            fl_row = c.execute("SELECT name FROM flocks WHERE id=?", (flock_id,)).fetchone()
            if fl_row: flock_name = fl_row["name"]

    # Initialize Density Tracker
    density_cfg = get_active_density_config()
    density_tracker = DensityTracker(
        config=density_cfg,
        job_id=job_id,
        output_dir=density_events_dir,
        farm_id=farm_id,
        flock_id=flock_id
    )

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError("OpenCV could not open video file. Verify file decodability and codec integrity.")

    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

    if total <= 0 or width <= 0 or height <= 0:
        cap.release()
        raise RuntimeError("Video metadata is invalid or the video has no decodable frames.")

    stride = max(1, settings.frame_stride)
    out_path = job_dir / "annotated.mp4"
    output_fps = min(fps if fps > 0 else 15.0, 30.0)

    writer = cv2.VideoWriter(
        str(out_path), 
        cv2.VideoWriter_fourcc(*"mp4v"), 
        output_fps, 
        (width, height)
    )
    if not writer.isOpened():
        cap.release()
        raise RuntimeError("Could not initialize VideoWriter for annotated output MP4.")

    observations = []
    track_history = defaultdict(list)
    seen_track_ids = set()
    prev_gray = None
    frame_idx = 0
    sampled_count = 0
    error = None
    inference_start = time.time()
    last_boxes = []

    is_coco = ("yolov8" in detector.model_path.lower() or "coco" in detector.model_path.lower()) and not bool(settings.custom_model_path.strip())

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            mr = compute_motion_ratio(prev_gray, gray)
            prev_gray = gray

            ts = round(frame_idx / fps if fps > 0 else 0.0, 3)

            if frame_idx % stride == 0:
                sampled_count += 1
                boxes = detector.track_frame(frame)
                last_boxes = boxes

                # Record track coordinates
                frame_track_ids = []
                for b in boxes:
                    tid = b.get("track_id")
                    if tid is not None:
                        frame_track_ids.append(tid)
                        seen_track_ids.add(tid)
                        x1, y1, x2, y2 = b["xyxy"]
                        cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
                        track_history[tid].append((ts, cx, cy))

                ds = compute_density_score(boxes, width, height)

                # Process Spatial High-Density Screening
                new_density_events = density_tracker.process_frame(frame_idx, ts, frame, boxes)
                for de in new_density_events:
                    aid = None
                    with db.connect() as c:
                        # 1. Persist density event
                        c.execute(
                            """INSERT INTO density_events
                               (id, job_id, farm_id, flock_id, zone_id, grid_layout, frame_index, timestamp_sec,
                                detection_count, threshold, occupied_area_pct, start_time_sec, end_time_sec,
                                duration_sec, persistence_frames, evidence_original_path, evidence_annotated_path,
                                trigger_reason, review_status)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                de.id, de.job_id, de.farm_id, de.flock_id, de.zone_id, de.grid_layout,
                                de.frame_index, de.timestamp_sec, de.detection_count, de.threshold,
                                de.occupied_area_pct, de.start_time_sec, de.end_time_sec, de.duration_sec,
                                de.persistence_frames, de.evidence_original_path, de.evidence_annotated_path,
                                de.trigger_reason, de.review_status
                            )
                        )

                        # 2. Automatically generate review alert linked to density event
                        alert_title = f"High Spatial Concentration: {flock_name} ({de.zone_id})"
                        alert_msg = (
                            f"Persistent concentration detected in Zone {de.zone_id} ({de.detection_count} birds, "
                            f"threshold {de.threshold}). Review evidence frame at {de.timestamp_sec:.1f}s."
                        )
                        cur = c.execute(
                            """INSERT INTO alerts
                               (farm_id, flock_id, job_id, severity, title, message, alert_type, density_event_id)
                               VALUES (?, ?, ?, 'review', ?, ?, 'density_review', ?)""",
                            (de.farm_id, de.flock_id, de.job_id, alert_title, alert_msg, de.id)
                        )
                        aid = cur.lastrowid

                    # 3. Dispatch SMS alert if enabled (outside DB transaction)
                    sms_text = format_sms_message(
                        category="persistent_density",
                        farm_name=farm_name,
                        flock_name=flock_name,
                        zone_id=de.zone_id,
                        time_str=f"{de.timestamp_sec:.1f}s",
                        count=de.detection_count,
                        alert_id=aid
                    )
                    dispatch_alert_sms("persistent_density", sms_text, alert_id=aid)

                obs = {
                    "frame_index": frame_idx,
                    "timestamp_sec": ts,
                    "detections": len(boxes),
                    "track_ids": frame_track_ids,
                    "boxes": boxes,
                    "motion_ratio": mr,
                    "density_score": ds
                }
                observations.append(obs)

                # Persist observation in SQLite
                with db.connect() as c:
                    c.execute(
                        "INSERT INTO observations(job_id,frame_index,timestamp_sec,detections,track_ids_json,boxes_json,motion_ratio,density_score) VALUES(?,?,?,?,?,?,?,?)",
                        (job_id, frame_idx, ts, len(boxes), json.dumps(frame_track_ids), json.dumps(boxes), mr, ds)
                    )

                # Save sampled raw frame JPEG
                if settings.save_frames:
                    frame_filename = f"frame_{frame_idx:08d}.jpg"
                    cv2.imwrite(str(frames_dir / frame_filename), frame)

                # Periodic progress update in DB
                if sampled_count % 10 == 0:
                    pct = round(min(99.0, (frame_idx / max(1, total)) * 100.0), 1)
                    with db.connect() as c:
                        c.execute("UPDATE jobs SET progress_percent=? WHERE id=?", (pct, job_id))

            # Annotate frame
            draw_clean_annotations(
                frame, 
                last_boxes, 
                frame_idx, 
                len(last_boxes), 
                len(seen_track_ids), 
                ts, 
                is_coco,
                density_config=density_cfg
            )
            writer.write(frame)
            frame_idx += 1

    except Exception as exc:
        error = str(exc)
    finally:
        cap.release()
        writer.release()

    if error:
        raise RuntimeError(error)

    if sampled_count == 0:
        raise RuntimeError("No frames were sampled during analysis. Check frame_stride setting.")

    total_proc_time = round(time.time() - inference_start, 2)
    fps_measured = round(sampled_count / max(0.001, total_proc_time), 2)

    # Compute Behavioral Indicators from trajectories & observations
    behavior_indicators = compute_behavioral_indicators(
        observations=observations,
        track_history=track_history,
        video_fps=fps,
        video_duration_sec=round(total / fps, 2) if fps > 0 else 0.0
    )

    # Compute Spatial Density Grid Heatmap Summary
    density_grid_summary = compute_density_grid_summary(
        observations=observations,
        rows=density_cfg.grid_rows,
        cols=density_cfg.grid_cols,
        width=width,
        height=height
    )

    counts = [x["detections"] for x in observations]
    zero_detections = sum(v == 0 for v in counts)
    mean_count = round(float(np.mean(counts)), 2)
    median_count = float(np.median(counts))
    max_count = int(max(counts)) if counts else 0
    min_count = int(min(counts)) if counts else 0
    mean_density = round(float(np.mean([o["density_score"] for o in observations])), 4)
    mean_motion = round(float(np.mean([o["motion_ratio"] for o in observations])), 5)

    summary = {
        "job_id": job_id,
        "video": Path(video_path).name,
        "status": "completed",
        "video_duration_sec": round(total / fps, 2) if fps > 0 else 0.0,
        "video_fps": round(fps, 2),
        "resolution": f"{width}x{height}",
        "total_video_frames": total,
        "sampled_frames": sampled_count,
        "frame_stride": stride,
        "processing_time_sec": total_proc_time,
        "processing_fps": fps_measured,
        "mean_detections_per_frame": mean_count,
        "median_detections": median_count,
        "max_detections_in_single_frame": max_count,
        "min_detections_in_single_frame": min_count,
        "zero_detection_fraction": round(zero_detections / sampled_count, 4),
        "unique_track_identities_observed": len(seen_track_ids),
        "mean_motion_ratio": mean_motion,
        "mean_density_score": mean_density,
        "density_config": density_cfg.to_dict(),
        "density_events_triggered_count": len(density_tracker.recorded_events),
        "density_grid_distribution": density_grid_summary,
        "behavioral_indicators": behavior_indicators,
        "model_used": detector.model_path,
        "inference_device": detector.device,
        "is_coco_proxy": is_coco,
        "detection_scope": (
            "Generic COCO bird proxy; detections represent visible bird-like forms, not confirmed flock headcounts." 
            if is_coco else "Custom poultry detection weights."
        ),
        "accuracy_warning": "Detection and tracking counts are screening proxies. Quantitative accuracy requires labeled ground truth.",
        "annotated_video_path": str(out_path.resolve()),
        "frames_directory": str(frames_dir.resolve()) if settings.save_frames else None
    }

    # Save summary.json
    with open(job_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Save observations.json
    with open(job_dir / "observations.json", "w", encoding="utf-8") as f:
        json.dump(observations, f, indent=2)

    # Save density_events.json
    with open(job_dir / "density_events.json", "w", encoding="utf-8") as f:
        json.dump([e.to_dict() for e in density_tracker.recorded_events], f, indent=2)

    # Save observations.csv
    with open(job_dir / "observations.csv", "w", newline="", encoding="utf-8") as f:
        fields = ["frame_index", "timestamp_sec", "detections", "track_ids", "motion_ratio", "density_score"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for o in observations:
            w.writerow({
                "frame_index": o["frame_index"],
                "timestamp_sec": o["timestamp_sec"],
                "detections": o["detections"],
                "track_ids": ";".join(str(tid) for tid in o["track_ids"]),
                "motion_ratio": o["motion_ratio"],
                "density_score": o["density_score"]
            })

    # Update job record in SQLite
    with db.connect() as c:
        c.execute(
            """UPDATE jobs SET 
               status='completed', 
               progress_percent=100.0, 
               finished_at=CURRENT_TIMESTAMP, 
               density_config_json=?, 
               result_json=? 
               WHERE id=?""",
            (json.dumps(density_cfg.to_dict()), json.dumps(summary), job_id)
        )
        
        # Automated triage review alert: low detector coverage
        if summary["zero_detection_fraction"] >= 0.5:
            c.execute(
                """INSERT INTO alerts(farm_id, flock_id, job_id, severity, title, message, alert_type) 
                   VALUES(?,?,?,?,?,?, 'system_quality')""",
                (farm_id, flock_id, job_id, "review", "Low detector coverage in video",
                 f"Over 50% of sampled frames ({summary['zero_detection_fraction']*100:.1f}%) had 0 detections. Check coop lighting, camera angle, or detector sensitivity.")
            )

        # Automated behavioral alert: persistent flock lethargy / high stationary ratio
        behavioral_aid = None
        mv_metrics = behavior_indicators.get("movement_metrics", {})
        if mv_metrics.get("inactivity_risk") == "high_inactivity":
            cur = c.execute(
                """INSERT INTO alerts(farm_id, flock_id, job_id, severity, title, message, alert_type)
                   VALUES(?,?,?, 'watch', ?, ?, 'behavioral_screening')""",
                (farm_id, flock_id, job_id, f"High Flock Inactivity Screening: {flock_name}",
                 mv_metrics.get("inactivity_notes", "Over 70% of tracked birds exhibited persistent low movement."))
            )
            behavioral_aid = cur.lastrowid

    if behavioral_aid:
        sms_text = format_sms_message(
            category="unusual_activity",
            farm_name=farm_name,
            flock_name=flock_name,
            alert_id=behavioral_aid
        )
        dispatch_alert_sms("unusual_activity", sms_text, alert_id=behavioral_aid)

    return summary
