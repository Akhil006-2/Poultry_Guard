from pathlib import Path
import json

def inspect_datasets():
    # 1. Chicken-Behavior-Analysis annotations
    cba_anno3 = Path(r"C:\Dev\12hr\Chicken-Behavior-Analysis\Annotation\anno3.txt")
    cba_img_dir = Path(r"C:\Dev\12hr\Chicken-Behavior-Analysis\img")
    if cba_anno3.exists():
        with open(cba_anno3, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        print(f"CBA anno3 lines: {len(lines)}")
        matched_images = 0
        total_boxes = 0
        for line in lines:
            parts = line.split()
            img_name = parts[0]
            boxes = parts[1:]
            total_boxes += len(boxes)
            if (cba_img_dir / img_name).exists():
                matched_images += 1
        print(f"CBA matched images in img/: {matched_images}/{len(lines)}, total annotated boxes: {total_boxes}")

    # 2. poultry_behaviour_dataset annotations
    pbd_dir = Path(r"C:\Dev\12hr\poultry_behaviour_dataset\poultry_behaviour_dataset\chickens")
    for job_dir in sorted(pbd_dir.glob("job_*")):
        anno_file = job_dir / f"annotations_{job_dir.name.split('_')[1]}.json"
        video_files = list(job_dir.glob("*.mp4"))
        if anno_file.exists():
            with open(anno_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            frames = data.get("frames", [])
            total_gt_boxes = sum(len(fr.get("tracks_bbox", [])) for fr in frames)
            print(f"PBD {job_dir.name}: frames={len(frames)}, total gt boxes={total_gt_boxes}, videos={[v.name for v in video_files]}")

if __name__ == "__main__":
    inspect_datasets()
