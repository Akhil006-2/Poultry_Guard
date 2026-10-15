"""PoultryGuard Spatial High-Density Screening Module

Implements spatial partitioning (2x2, 3x3, 4x4 grids), bounding-box zone assignment,
per-zone bird counting and occupied area estimation, persistence temporal tracking,
clearing hysteresis, event deduplication, and evidence frame capture.

Notice: This module measures image-space concentration (birds per pixel area),
which serves as a behavioral screening proxy for flock clustering/crowding.
It does NOT represent physical stocking density (birds/m^2) without calibrated floor geometry.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import cv2
import numpy as np


@dataclass
class DensityConfig:
    """Configuration for spatial high-density screening."""
    grid_rows: int = 3
    grid_cols: int = 3
    count_threshold: int = 4
    area_threshold_pct: float = 12.0
    persistence_frames: int = 3
    clearing_threshold: int = 2
    clearing_frames: int = 2
    enabled_zones: Optional[List[str]] = None

    @property
    def layout_name(self) -> str:
        return f"{self.grid_rows}x{self.grid_cols}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "grid_rows": self.grid_rows,
            "grid_cols": self.grid_cols,
            "layout": self.layout_name,
            "count_threshold": self.count_threshold,
            "area_threshold_pct": self.area_threshold_pct,
            "persistence_frames": self.persistence_frames,
            "clearing_threshold": self.clearing_threshold,
            "clearing_frames": self.clearing_frames,
            "enabled_zones": self.enabled_zones,
        }


def get_zone_id(row: int, col: int) -> str:
    """Human-readable zone identifier, e.g. A1, B2, C3."""
    row_char = chr(ord('A') + row)
    return f"{row_char}{col + 1}"


def get_zone_rect(row: int, col: int, rows: int, cols: int, width: int, height: int) -> Tuple[int, int, int, int]:
    """Returns (x1, y1, x2, y2) bounds of a grid cell."""
    cell_w = width / cols
    cell_h = height / rows
    x1 = int(round(col * cell_w))
    y1 = int(round(row * cell_h))
    x2 = int(round((col + 1) * cell_w)) if col < cols - 1 else width
    y2 = int(round((row + 1) * cell_h)) if row < rows - 1 else height
    return x1, y1, x2, y2


def assign_boxes_to_zones(
    boxes: List[Dict[str, Any]],
    rows: int,
    cols: int,
    width: int,
    height: int
) -> Dict[str, List[Dict[str, Any]]]:
    """Assigns detections to grid zones based on their bounding-box center."""
    zone_boxes: Dict[str, List[Dict[str, Any]]] = {
        get_zone_id(r, c): [] for r in range(rows) for c in range(cols)
    }

    if width <= 0 or height <= 0:
        return zone_boxes

    cell_w = width / cols
    cell_h = height / rows

    for box in boxes:
        xyxy = box.get("xyxy", [0, 0, 0, 0])
        cx = (xyxy[0] + xyxy[2]) / 2.0
        cy = (xyxy[1] + xyxy[3]) / 2.0

        r = int(min(rows - 1, max(0, int(cy // cell_h))))
        c = int(min(cols - 1, max(0, int(cx // cell_w))))
        zid = get_zone_id(r, c)
        zone_boxes[zid].append(box)

    return zone_boxes


def compute_zone_occupied_area_pct(
    boxes_in_zone: List[Dict[str, Any]],
    zone_rect: Tuple[int, int, int, int]
) -> float:
    """Calculates percentage of zone area covered by detection bounding boxes."""
    zx1, zy1, zx2, zy2 = zone_rect
    zw = max(1, zx2 - zx1)
    zh = max(1, zy2 - zy1)

    if not boxes_in_zone:
        return 0.0

    # Downsampled mask for fast computation without double counting overlapping boxes
    mask_w = 160
    mask_h = 120
    mask = np.zeros((mask_h, mask_w), dtype=np.uint8)

    scale_x = mask_w / float(zw)
    scale_y = mask_h / float(zh)

    for b in boxes_in_zone:
        bx1, by1, bx2, by2 = b.get("xyxy", [0, 0, 0, 0])
        # Clip to zone boundaries
        ix1 = max(zx1, min(zx2, bx1))
        iy1 = max(zy1, min(zy2, by1))
        ix2 = max(zx1, min(zx2, bx2))
        iy2 = max(zy1, min(zy2, by2))

        if ix2 > ix1 and iy2 > iy1:
            mx1 = int((ix1 - zx1) * scale_x)
            my1 = int((iy1 - zy1) * scale_y)
            mx2 = int((ix2 - zx1) * scale_x)
            my2 = int((iy2 - zy1) * scale_y)
            mask[max(0, my1):min(mask_h, my2), max(0, mx1):min(mask_w, mx2)] = 255

    occupied = float(np.count_nonzero(mask)) / float(mask_w * mask_h)
    return round(occupied * 100.0, 2)


@dataclass
class DensityEventRecord:
    """Persisted record of a high-density event."""
    id: str
    job_id: str
    farm_id: Optional[int]
    flock_id: Optional[int]
    zone_id: str
    grid_layout: str
    frame_index: int
    timestamp_sec: float
    detection_count: int
    threshold: int
    occupied_area_pct: float
    start_time_sec: float
    end_time_sec: float
    duration_sec: float
    persistence_frames: int
    evidence_original_path: str
    evidence_annotated_path: str
    trigger_reason: str
    review_status: str = "pending_review"
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "job_id": self.job_id,
            "farm_id": self.farm_id,
            "flock_id": self.flock_id,
            "zone_id": self.zone_id,
            "grid_layout": self.grid_layout,
            "frame_index": self.frame_index,
            "timestamp_sec": self.timestamp_sec,
            "detection_count": self.detection_count,
            "threshold": self.threshold,
            "occupied_area_pct": self.occupied_area_pct,
            "start_time_sec": self.start_time_sec,
            "end_time_sec": self.end_time_sec,
            "duration_sec": self.duration_sec,
            "persistence_frames": self.persistence_frames,
            "evidence_original_path": self.evidence_original_path,
            "evidence_annotated_path": self.evidence_annotated_path,
            "trigger_reason": self.trigger_reason,
            "review_status": self.review_status,
            "notes": self.notes
        }


class DensityTracker:
    """Stateful tracker for spatial concentration across consecutive frames."""

    def __init__(
        self,
        config: DensityConfig,
        job_id: str,
        output_dir: Path,
        farm_id: Optional[int] = None,
        flock_id: Optional[int] = None
    ):
        self.config = config
        self.job_id = job_id
        self.output_dir = output_dir
        self.farm_id = farm_id
        self.flock_id = flock_id

        # Internal state per zone: zone_id -> dict
        # {
        #   "consecutive_high_frames": int,
        #   "consecutive_low_frames": int,
        #   "active_event": Optional[DensityEventRecord],
        #   "start_frame": int,
        #   "start_ts": float
        # }
        self.zone_states: Dict[str, Dict[str, Any]] = {}
        for r in range(config.grid_rows):
            for c in range(config.grid_cols):
                zid = get_zone_id(r, c)
                self.zone_states[zid] = {
                    "consecutive_high_frames": 0,
                    "consecutive_low_frames": 0,
                    "active_event": None,
                    "start_frame": 0,
                    "start_ts": 0.0,
                }

        self.recorded_events: List[DensityEventRecord] = []
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def process_frame(
        self,
        frame_idx: int,
        timestamp_sec: float,
        frame_bgr: np.ndarray,
        boxes: List[Dict[str, Any]]
    ) -> List[DensityEventRecord]:
        """Processes a single sampled frame, updating persistence states and returning any newly triggered events."""
        h, w = frame_bgr.shape[:2]
        zone_boxes = assign_boxes_to_zones(boxes, self.config.grid_rows, self.config.grid_cols, w, h)
        new_events: List[DensityEventRecord] = []

        for r in range(self.config.grid_rows):
            for c in range(self.config.grid_cols):
                zid = get_zone_id(r, c)

                # Skip disabled zones if configured
                if self.config.enabled_zones is not None and zid not in self.config.enabled_zones:
                    continue

                state = self.zone_states[zid]
                z_rect = get_zone_rect(r, c, self.config.grid_rows, self.config.grid_cols, w, h)
                boxes_in_zone = zone_boxes.get(zid, [])
                count = len(boxes_in_zone)
                area_pct = compute_zone_occupied_area_pct(boxes_in_zone, z_rect)

                # Condition for high density in zone
                is_high = (count >= self.config.count_threshold) and (area_pct >= self.config.area_threshold_pct or self.config.area_threshold_pct <= 0)

                if is_high:
                    state["consecutive_high_frames"] += 1
                    state["consecutive_low_frames"] = 0

                    if state["active_event"] is None:
                        if state["consecutive_high_frames"] == 1:
                            state["start_frame"] = frame_idx
                            state["start_ts"] = timestamp_sec

                        # Persistence condition satisfied: TRIGGER EVENT!
                        if state["consecutive_high_frames"] >= self.config.persistence_frames:
                            event_id = f"de_{uuid.uuid4().hex[:12]}"
                            trigger_reason = (
                                f"High concentration in {zid}: {count} birds (threshold {self.config.count_threshold}) "
                                f"covering {area_pct}% area, sustained for {state['consecutive_high_frames']} frames."
                            )

                            # Save evidence frames
                            orig_path, anno_path = self._save_evidence_images(
                                event_id, frame_bgr, boxes, zid, z_rect, count, area_pct, timestamp_sec
                            )

                            event_rec = DensityEventRecord(
                                id=event_id,
                                job_id=self.job_id,
                                farm_id=self.farm_id,
                                flock_id=self.flock_id,
                                zone_id=zid,
                                grid_layout=self.config.layout_name,
                                frame_index=frame_idx,
                                timestamp_sec=round(timestamp_sec, 2),
                                detection_count=count,
                                threshold=self.config.count_threshold,
                                occupied_area_pct=area_pct,
                                start_time_sec=round(state["start_ts"], 2),
                                end_time_sec=round(timestamp_sec, 2),
                                duration_sec=round(max(0.0, timestamp_sec - state["start_ts"]), 2),
                                persistence_frames=self.config.persistence_frames,
                                evidence_original_path=orig_path,
                                evidence_annotated_path=anno_path,
                                trigger_reason=trigger_reason,
                                review_status="pending_review"
                            )

                            state["active_event"] = event_rec
                            self.recorded_events.append(event_rec)
                            new_events.append(event_rec)
                    else:
                        # Event already active; update duration without generating a duplicate alert
                        active = state["active_event"]
                        active.end_time_sec = round(timestamp_sec, 2)
                        active.duration_sec = round(timestamp_sec - active.start_time_sec, 2)
                        if count > active.detection_count:
                            active.detection_count = count
                            active.occupied_area_pct = area_pct

                else:
                    # Not high density
                    if count <= self.config.clearing_threshold:
                        state["consecutive_low_frames"] += 1
                    else:
                        state["consecutive_low_frames"] = 0

                    state["consecutive_high_frames"] = 0

                    # Check clearing hysteresis
                    if state["active_event"] is not None and state["consecutive_low_frames"] >= self.config.clearing_frames:
                        # Clear active event state so future clusters can trigger anew
                        state["active_event"] = None
                        state["consecutive_low_frames"] = 0

        return new_events

    def _save_evidence_images(
        self,
        event_id: str,
        frame_bgr: np.ndarray,
        boxes: List[Dict[str, Any]],
        zone_id: str,
        zone_rect: Tuple[int, int, int, int],
        count: int,
        area_pct: float,
        timestamp_sec: float
    ) -> Tuple[str, str]:
        """Generates and saves the original frame and annotated evidence frame."""
        h, w = frame_bgr.shape[:2]

        # 1. Original clean frame
        orig_filename = f"{event_id}_original.jpg"
        orig_full_path = self.output_dir / orig_filename
        cv2.imwrite(str(orig_full_path), frame_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 92])

        # 2. Annotated frame with highlighted zone, grid, and detection boxes
        anno = frame_bgr.copy()
        overlay = anno.copy()

        # Draw full grid lines
        for r in range(1, self.config.grid_rows):
            gy = int(round(r * (h / self.config.grid_rows)))
            cv2.line(overlay, (0, gy), (w, gy), (180, 200, 220), 1, cv2.LINE_AA)
        for c in range(1, self.config.grid_cols):
            gx = int(round(c * (w / self.config.grid_cols)))
            cv2.line(overlay, (gx, 0), (gx, h), (180, 200, 220), 1, cv2.LINE_AA)

        # Highlight triggered zone with semi-transparent amber/red tint
        zx1, zy1, zx2, zy2 = zone_rect
        cv2.rectangle(overlay, (zx1, zy1), (zx2, zy2), (0, 70, 230), -1)
        cv2.addWeighted(overlay, 0.35, anno, 0.65, 0, anno)

        # Bold border around the highlighted zone
        cv2.rectangle(anno, (zx1, zy1), (zx2, zy2), (0, 70, 255), 3)

        # Draw detection bounding boxes
        for b in boxes:
            bx1, by1, bx2, by2 = b.get("xyxy", [0, 0, 0, 0])
            tid = b.get("track_id")
            conf = b.get("confidence", 0.0)

            # Check if this box center is inside the active zone
            bcx, bcy = (bx1 + bx2) / 2.0, (by1 + by2) / 2.0
            in_zone = (zx1 <= bcx <= zx2) and (zy1 <= bcy <= zy2)

            box_color = (0, 255, 255) if in_zone else (100, 200, 100)
            cv2.rectangle(anno, (bx1, by1), (bx2, by2), box_color, 2)

            tag = f"#{tid}" if tid is not None else f"{conf:.2f}"
            cv2.putText(anno, tag, (bx1 + 2, max(12, by1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2, cv2.LINE_AA)
            cv2.putText(anno, tag, (bx1 + 2, max(12, by1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        # Add Header Overlay Banner
        banner_h = 56
        banner_overlay = anno.copy()
        cv2.rectangle(banner_overlay, (0, 0), (w, banner_h), (20, 25, 30), -1)
        cv2.addWeighted(banner_overlay, 0.85, anno, 0.15, 0, anno)

        header_l1 = (
            f"PoultryGuard Spatial High-Density Screening | {self.config.layout_name} Grid | "
            f"Zone: {zone_id} | Count: {count} (Threshold: {self.config.count_threshold}) | "
            f"Area: {area_pct}% | Time: {timestamp_sec:.1f}s"
        )
        header_l2 = "REVIEW REQUIRED -- Image-space concentration indicator. Not a veterinary disease diagnosis."

        cv2.putText(anno, header_l1, (12, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(anno, header_l2, (12, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 220, 240), 1, cv2.LINE_AA)

        # Label on the zone itself
        zone_label = f"Triggered Zone {zone_id} ({count} birds)"
        cv2.putText(anno, zone_label, (zx1 + 10, zy1 + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(anno, zone_label, (zx1 + 10, zy1 + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2, cv2.LINE_AA)

        anno_filename = f"{event_id}_annotated.jpg"
        anno_full_path = self.output_dir / anno_filename
        cv2.imwrite(str(anno_full_path), anno, [int(cv2.IMWRITE_JPEG_QUALITY), 92])

        # Return relative storage paths for portability
        rel_orig = f"jobs/{self.job_id}/density_events/{orig_filename}"
        rel_anno = f"jobs/{self.job_id}/density_events/{anno_filename}"
        return rel_orig, rel_anno


def compute_density_grid_summary(
    observations: List[Dict[str, Any]],
    rows: int = 3,
    cols: int = 3,
    width: int = 1920,
    height: int = 1080
) -> Dict[str, Any]:
    """Computes spatial concentration statistics and heatmap distribution over an entire video's observations."""
    zone_counts: Dict[str, int] = {get_zone_id(r, c): 0 for r in range(rows) for c in range(cols)}
    total_detections = 0
    sampled_frames = len(observations)

    for obs in observations:
        boxes = obs.get("boxes", [])
        assigned = assign_boxes_to_zones(boxes, rows, cols, width, height)
        for zid, b_list in assigned.items():
            zone_counts[zid] += len(b_list)
            total_detections += len(b_list)

    # Average birds per sampled frame per zone
    zone_averages: Dict[str, float] = {}
    zone_shares_pct: Dict[str, float] = {}
    for zid, cnt in zone_counts.items():
        zone_averages[zid] = round(cnt / max(1, sampled_frames), 2)
        zone_shares_pct[zid] = round((cnt / max(1, total_detections)) * 100.0, 1) if total_detections > 0 else 0.0

    # Max concentration zone
    max_zone = max(zone_counts.items(), key=lambda x: x[1])[0] if zone_counts else "None"

    return {
        "grid_layout": f"{rows}x{cols}",
        "total_detections_aggregated": total_detections,
        "sampled_frames": sampled_frames,
        "zone_total_counts": zone_counts,
        "zone_averages_per_frame": zone_averages,
        "zone_shares_pct": zone_shares_pct,
        "peak_concentration_zone": max_zone,
        "peak_concentration_share_pct": zone_shares_pct.get(max_zone, 0.0),
        "spatial_disclaimer": "Grid statistics reflect image-space detector observations. Visual occlusion, feeders, and camera perspective affect zone counts."
    }
