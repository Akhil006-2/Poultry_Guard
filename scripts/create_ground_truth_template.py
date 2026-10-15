"""Create sampled frame JPEGs and a blank per-frame chicken-count ground-truth CSV."""
import argparse, csv, cv2
from pathlib import Path
p=argparse.ArgumentParser(); p.add_argument('video'); p.add_argument('--out',default='ground_truth_work'); p.add_argument('--every-seconds',type=float,default=2.0); a=p.parse_args()
src=Path(a.video); out=Path(a.out); frames=out/'frames'; frames.mkdir(parents=True,exist_ok=True)
cap=cv2.VideoCapture(str(src))
if not cap.isOpened(): raise SystemExit(f'Cannot open video: {src}')
fps=cap.get(cv2.CAP_PROP_FPS) or 25; step=max(1,int(fps*max(.1,a.every_seconds))); i=0; rows=[]
while True:
 ok,frame=cap.read()
 if not ok: break
 if i%step==0:
  name=f'frame_{i:08d}.jpg'; cv2.imwrite(str(frames/name),frame); rows.append({'frame_index':i,'timestamp_sec':round(i/fps,3),'frame_file':name,'ground_truth_count':''})
 i+=1
cap.release()
with open(out/'ground_truth_counts.csv','w',newline='',encoding='utf-8') as f:
 w=csv.DictWriter(f,fieldnames=['frame_index','timestamp_sec','frame_file','ground_truth_count']); w.writeheader(); w.writerows(rows)
print(f'Saved {len(rows)} frames and blank count template to {out.resolve()}')
