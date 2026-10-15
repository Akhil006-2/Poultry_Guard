"""Standalone Poultry Video Detection & Tracking Script
---------------------------------------------------------
This script reads a raw poultry-house video, detects and tracks birds across frames
using YOLOv8 and ByteTrack, draws clean bounding boxes and tracking IDs, and saves
the resulting annotated video locally.

No arguments are required to run this script - the input and output paths are configured
directly below. You can also pass a custom video path as a command-line argument if desired.

Run with:
    python generate_annotated_video.py
or:
    python generate_annotated_video.py "path/to/custom_video.mp4"
"""

import sys
import time
from pathlib import Path
from collections import defaultdict
import cv2
import numpy as np

# ==============================================================================
# 1. HARDCODED CONFIGURATION (Edit these paths as needed)
# ==============================================================================

# Default raw video file to process
DEFAULT_INPUT_VIDEO = r"C:\Dev\12hr\PoultryGuard_Complete\poultry_videos\10.2.39.193_01_2025031406531250.mp4"

# Alternative fallback videos if the above is not found:
FALLBACK_VIDEOS = [
    r"C:\Dev\12hr\PoultryGuard_Complete\poultry_videos\10.2.39.190_01_20250314063356622.mp4",
    r"C:\Dev\12hr\poultry_behaviour_dataset\poultry_behaviour_dataset\chickens\job_000004\job_000004_400frames.mp4"
]

# Local directory where output video and summary will be saved
OUTPUT_DIR = Path(__file__).resolve().parent / "local_output"

# YOLO model weights (uses yolov8s.pt located in this project directory)
MODEL_WEIGHTS = Path(__file__).resolve().parent / "yolov8s.pt"

# Frame sampling stride:
# 1 = process every single frame (highest detail, takes longer)
# 2 = process every 2nd frame
# 3 = process every 3rd frame (recommended for fast balance of speed & tracking)
FRAME_STRIDE = 2

# Detection confidence threshold (0.05 - 0.20)
CONF_THRESHOLD = 0.08

# Image input size for YOLO inference (640 or 960)
IMAGE_SIZE = 640

# ==============================================================================
# 2. MAIN PROCESSING PIPELINE
# ==============================================================================

def resolve_input_video() -> Path:
    """Find input video from CLI argument, default path, or fallback paths."""
    if len(sys.argv) > 1 and sys.argv[1].strip():
        cli_path = Path(sys.argv[1]).resolve()
        if cli_path.is_file():
            return cli_path
        print(f"Warning: CLI video '{cli_path}' not found. Trying default path...")

    default_path = Path(DEFAULT_INPUT_VIDEO)
    if default_path.is_file():
        return default_path

    for fb in FALLBACK_VIDEOS:
        fb_path = Path(fb)
        if fb_path.is_file():
            print(f"Notice: Default video not found. Using fallback: {fb_path.name}")
            return fb_path

    raise FileNotFoundError(
        f"Could not find raw video at '{DEFAULT_INPUT_VIDEO}'. Please verify the path."
    )

def main():
    print("=" * 65)
    print("  POULTRYGUARD: STANDALONE VIDEO DETECTION & TRACKING")
    print("=" * 65)

    # 1. Resolve Input Video
    input_video_path = resolve_input_video()
    print(f"\n[+] Raw Input Video : {input_video_path}")
    print(f"[+] Output Directory : {OUTPUT_DIR}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_video_path = OUTPUT_DIR / f"annotated_{input_video_path.stem}.mp4"

    # 2. Load YOLO Model
    print(f"[+] Loading YOLO model from : {MODEL_WEIGHTS} ...")
    try:
        from ultralytics import YOLO
    except ImportError:
        print("ERROR: 'ultralytics' package not installed. Run: pip install ultralytics lap")
        sys.exit(1)

    if not MODEL_WEIGHTS.exists():
        print(f"Notice: '{MODEL_WEIGHTS}' not found locally. Will use 'yolov8s.pt'")
        model_target = "yolov8s.pt"
    else:
        model_target = str(MODEL_WEIGHTS)

    model = YOLO(model_target)
    print(f"    Loaded model successfully. (Device: {'GPU' if cv2.cuda.getCudaEnabledDeviceCount() > 0 else 'CPU'})")

    # 3. Open Video with OpenCV
    cap = cv2.VideoCapture(str(input_video_path))
    if not cap.isOpened():
        print(f"ERROR: OpenCV could not open video file: {input_video_path}")
        sys.exit(1)

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 360)

    duration_sec = total_frames / fps if fps > 0 else 0
    print(f"[+] Video Properties : {width}x{height} @ {fps:.1f} FPS | Total Frames: {total_frames} (~{duration_sec:.1f}s)")

    # 4. Setup Video Writer
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out_fps = max(10.0, fps)
    writer = cv2.VideoWriter(str(output_video_path), fourcc, out_fps, (width, height))

    if not writer.isOpened():
        print("ERROR: Failed to open OpenCV VideoWriter for output MP4.")
        cap.release()
        sys.exit(1)

    print(f"[+] Processing video with ByteTrack (Sampling every {FRAME_STRIDE} frames)...")

    # Tracking & Observation State
    seen_track_ids = set()
    frame_idx = 0
    sampled_count = 0
    last_boxes = []
    max_birds_in_frame = 0
    total_detections_sum = 0
    start_time = time.time()

    # 5. Process Frame-by-Frame
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            timestamp_sec = frame_idx / fps if fps > 0 else 0.0

            # Only run heavy neural detector on sampled frames (e.g. every 2nd or 3rd frame)
            if frame_idx % FRAME_STRIDE == 0:
                sampled_count += 1

                # Track chickens using ByteTrack (COCO class 14 = bird proxy)
                try:
                    results = model.track(
                        source=frame,
                        persist=True,
                        tracker="bytetrack.yaml",
                        classes=[14],
                        conf=CONF_THRESHOLD,
                        imgsz=IMAGE_SIZE,
                        verbose=False
                    )
                except Exception:
                    # Fallback to standard prediction if tracker encounters any issue
                    results = model.predict(
                        source=frame,
                        classes=[14],
                        conf=CONF_THRESHOLD,
                        imgsz=IMAGE_SIZE,
                        verbose=False
                    )

                current_boxes = []
                if results and len(results) > 0 and results[0].boxes is not None:
                    res_boxes = results[0].boxes
                    xyxy_arr = res_boxes.xyxy.cpu().tolist()
                    conf_arr = res_boxes.conf.cpu().tolist()
                    id_arr = res_boxes.id.int().cpu().tolist() if res_boxes.id is not None else [None] * len(xyxy_arr)

                    for xyxy, conf_val, tid in zip(xyxy_arr, conf_arr, id_arr):
                        if tid is not None:
                            seen_track_ids.add(tid)
                        current_boxes.append({
                            "xyxy": [int(v) for v in xyxy],
                            "conf": float(conf_val),
                            "track_id": tid
                        })

                last_boxes = current_boxes
                count = len(last_boxes)
                max_birds_in_frame = max(max_birds_in_frame, count)
                total_detections_sum += count

                # Terminal progress logging every 25 sampled frames
                if sampled_count % 25 == 0 or sampled_count == 1:
                    pct = (frame_idx / max(1, total_frames)) * 100
                    elapsed = time.time() - start_time
                    fps_proc = sampled_count / max(0.001, elapsed)
                    print(f"    Progress: {pct:5.1f}% | Frame {frame_idx:4d}/{total_frames} | Live Count: {count:2d} | Unique Tracks: {len(seen_track_ids):2d} | Speed: {fps_proc:.1f} FPS")

            # 6. Draw Clean Annotations on Frame
            # Draw bounding boxes
            for b in last_boxes:
                x1, y1, x2, y2 = b["xyxy"]
                tid = b["track_id"]
                conf_val = b["conf"]

                # Green box for tracked bird, Cyan for untracked
                color = (0, 220, 90) if tid is not None else (255, 200, 0)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

                # Label tag: e.g. "#3 0.85"
                label = f"#{tid} {conf_val:.2f}" if tid is not None else f"{conf_val:.2f}"
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                cv2.rectangle(frame, (x1, max(0, y1 - th - 6)), (x1 + tw + 6, y1), color, -1)
                cv2.putText(frame, label, (x1 + 3, y1 - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)

            # Draw top telemetry banner (semi-transparent dark background)
            banner_h = 38
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (width, banner_h), (20, 25, 25), -1)
            cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

            header_text = f"PoultryGuard | Frame {frame_idx:04d} ({timestamp_sec:4.1f}s) | Detected Birds: {len(last_boxes):2d} | Cumulative Tracks: {len(seen_track_ids):2d}"
            cv2.putText(frame, header_text, (12, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2, cv2.LINE_AA)

            # Write annotated frame to output video
            writer.write(frame)
            frame_idx += 1

    finally:
        cap.release()
        writer.release()

    total_proc_time = time.time() - start_time
    avg_detections = total_detections_sum / max(1, sampled_count)
    proc_fps = sampled_count / max(0.001, total_proc_time)

    # 7. Print Completion Summary
    print("\n" + "=" * 65)
    print("  [SUCCESS] ANNOTATED VIDEO GENERATED AND SAVED LOCALLY!")
    print("=" * 65)
    print(f"Output Video Location : {output_video_path.resolve()}")
    print(f"Output File Size      : {output_video_path.stat().st_size / (1024 * 1024):.2f} MB")
    print(f"Sampled Frames Run    : {sampled_count} frames (Stride: {FRAME_STRIDE})")
    print(f"Total Processing Time : {total_proc_time:.2f} seconds ({proc_fps:.2f} FPS)")
    print(f"Peak Live Count       : {max_birds_in_frame} birds in a single frame")
    print(f"Average Live Count    : {avg_detections:.2f} birds / frame")
    print(f"Unique Track IDs      : {len(seen_track_ids)} birds tracked across video")
    print("=" * 65)
    print(f"\nYou can open and watch the video directly at:\n  {output_video_path.resolve()}\n")

if __name__ == "__main__":
    main()
