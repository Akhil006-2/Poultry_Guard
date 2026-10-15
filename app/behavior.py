"""PoultryGuard Early Behavioral Indicators Module

Computes interpretable screening indicators from tracking trajectories and frame observations:
- Movement and activity index (tracked bounding-box centroid displacement)
- Stationary bird fraction (proxy for flock lethargy / reduced movement)
- Temporal activity change relative to baseline
- Spatial concentration / clustering index
- Camera quality and detection coverage uncertainty (lighting, occlusion, frame failure)

All indicators are non-diagnostic screening signals intended to prompt flock inspection.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple, Any
import numpy as np


def compute_behavioral_indicators(
    observations: List[Dict[str, Any]],
    track_history: Dict[int, List[Tuple[float, float, float]]],
    video_fps: float = 15.0,
    video_duration_sec: float = 0.0,
    min_track_frames: int = 3,
    stationary_speed_threshold_px_s: float = 4.0
) -> Dict[str, Any]:
    """Computes flock behavioral screening indicators from video analysis observations.
    
    Args:
        observations: List of per-frame observation dictionaries.
        track_history: Mapping of track_id -> [(timestamp_sec, cx, cy), ...]
        video_fps: Framerate of video.
        video_duration_sec: Total duration of video in seconds.
        min_track_frames: Minimum sampled frames to consider a track valid for speed metrics.
        stationary_speed_threshold_px_s: Pixels per second displacement threshold below which a bird is considered stationary.
    """
    sampled_count = len(observations)
    if sampled_count == 0:
        return {
            "status": "insufficient_data",
            "message": "No sampled frames available for behavioral indicator screening."
        }

    counts = [o.get("detections", 0) for o in observations]
    motion_ratios = [o.get("motion_ratio", 0.0) for o in observations]
    density_scores = [o.get("density_score", 0.0) for o in observations]
    timestamps = [o.get("timestamp_sec", 0.0) for o in observations]

    # 1. Trajectory Speed & Inactivity / Stationary Screening
    track_speeds: List[float] = []
    track_displacements: List[float] = []
    stationary_count = 0
    active_count = 0

    for tid, trajectory in track_history.items():
        if len(trajectory) < min_track_frames:
            continue

        # Compute total path length
        disp = sum(
            math.hypot(trajectory[i][1] - trajectory[i-1][1], trajectory[i][2] - trajectory[i-1][2])
            for i in range(1, len(trajectory))
        )
        duration = trajectory[-1][0] - trajectory[0][0]
        speed = disp / max(0.1, duration)

        track_speeds.append(round(speed, 2))
        track_displacements.append(round(disp, 1))

        if speed < stationary_speed_threshold_px_s:
            stationary_count += 1
        else:
            active_count += 1

    total_tracked_birds = stationary_count + active_count
    stationary_ratio = round(stationary_count / max(1, total_tracked_birds), 3) if total_tracked_birds > 0 else 0.0
    mean_speed = round(float(np.mean(track_speeds)), 2) if track_speeds else 0.0
    median_speed = round(float(np.median(track_speeds)), 2) if track_speeds else 0.0

    # 2. Activity Trends: Baseline (first third) vs Final (last third)
    third = max(1, sampled_count // 3)
    baseline_motion = float(np.mean(motion_ratios[:third])) if sampled_count >= 3 else float(np.mean(motion_ratios))
    recent_motion = float(np.mean(motion_ratios[-third:])) if sampled_count >= 3 else float(np.mean(motion_ratios))
    motion_change_pct = round(((recent_motion - baseline_motion) / max(0.0001, baseline_motion)) * 100.0, 1)

    # 3. Detection Uncertainty & Sudden Drop Analysis
    zero_detection_frames = sum(c == 0 for c in counts)
    zero_detection_ratio = round(zero_detection_frames / max(1, sampled_count), 4)

    # Rolling window sudden drop check
    sudden_drops = 0
    for i in range(3, sampled_count):
        prior_avg = (counts[i-3] + counts[i-2] + counts[i-1]) / 3.0
        if prior_avg >= 4 and counts[i] <= (prior_avg * 0.35):
            sudden_drops += 1

    coverage_rating = "good"
    coverage_warning = ""
    if zero_detection_ratio > 0.5:
        coverage_rating = "critical_uncertainty"
        coverage_warning = f"High uncertainty: {zero_detection_ratio*100:.1f}% of sampled frames had 0 detections. Camera angle, lighting, or detection threshold require verification."
    elif zero_detection_ratio > 0.2 or sudden_drops >= 3:
        coverage_rating = "moderate_uncertainty"
        coverage_warning = f"Moderate uncertainty: {sudden_drops} abrupt count drops detected. Inspect coop lighting, feeding schedules, or physical occlusions."

    # 4. Inactivity Risk Assessment
    inactivity_risk = "normal"
    inactivity_notes = "Flock activity appears normal relative to baseline."
    if total_tracked_birds >= 5 and stationary_ratio >= 0.70:
        inactivity_risk = "high_inactivity"
        inactivity_notes = (
            f"Over {stationary_ratio*100:.0f}% of tracked birds exhibited persistent low movement "
            f"(< {stationary_speed_threshold_px_s} px/s). This may indicate resting behavior, thermal stress, or early malaise. Manual coop inspection recommended."
        )
    elif total_tracked_birds >= 5 and stationary_ratio >= 0.50:
        inactivity_risk = "moderate_inactivity"
        inactivity_notes = f"{stationary_ratio*100:.0f}% of tracked birds showed low movement. Monitor for changes in water or feed consumption."

    return {
        "status": "computed",
        "sampled_frames_analyzed": sampled_count,
        "video_duration_sec": video_duration_sec,
        "total_tracked_birds_evaluated": total_tracked_birds,
        "movement_metrics": {
            "mean_tracked_speed_px_s": mean_speed,
            "median_tracked_speed_px_s": median_speed,
            "stationary_speed_threshold_px_s": stationary_speed_threshold_px_s,
            "stationary_birds_count": stationary_count,
            "active_birds_count": active_count,
            "stationary_bird_ratio": stationary_ratio,
            "inactivity_risk": inactivity_risk,
            "inactivity_notes": inactivity_notes,
            "mean_frame_motion_ratio": round(float(np.mean(motion_ratios)), 5),
            "baseline_motion_ratio": round(baseline_motion, 5),
            "recent_motion_ratio": round(recent_motion, 5),
            "activity_change_vs_baseline_pct": motion_change_pct
        },
        "coverage_and_uncertainty": {
            "zero_detection_frames": zero_detection_frames,
            "zero_detection_ratio": zero_detection_ratio,
            "sudden_detection_drops": sudden_drops,
            "coverage_rating": coverage_rating,
            "coverage_warning": coverage_warning
        },
        "screening_disclaimer": (
            "Screening Guidance: Behavioral indicators are automated proxy metrics derived from bounding box tracking. "
            "They support operational flock oversight but do NOT constitute clinical diagnosis of contagious avian disease. "
            "Suspected flock health issues must be verified by a qualified veterinarian."
        )
    }
