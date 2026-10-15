import argparse, cv2
from pathlib import Path
p=argparse.ArgumentParser(description='Extract frames from a video at a chosen interval')
p.add_argument('video'); p.add_argument('--out',default='extracted_frames'); p.add_argument('--every-seconds',type=float,default=2.0)
a=p.parse_args(); src=Path(a.video); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
cap=cv2.VideoCapture(str(src))
if not cap.isOpened(): raise SystemExit(f'Cannot open video: {src}')
fps=cap.get(cv2.CAP_PROP_FPS) or 25; step=max(1,int(fps*max(.1,a.every_seconds))); i=0; saved=0
while True:
 ok,frame=cap.read()
 if not ok: break
 if i%step==0:
  path=out/f'{src.stem}_frame_{i:08d}.jpg'
  if cv2.imwrite(str(path),frame): saved+=1
 i+=1
cap.release(); print(f'Read {i} frames; saved {saved} frames to {out.resolve()}')
