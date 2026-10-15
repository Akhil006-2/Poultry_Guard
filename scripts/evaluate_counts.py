"""Compare predicted per-frame counts with manually recorded counts in a CSV.
Expected columns: frame_index,ground_truth_count. Prediction CSV has frame_index,detections.
Reports MAE, RMSE, and count bias; it does not calculate box-level precision/recall.
"""
import argparse,csv,json,math
from pathlib import Path
p=argparse.ArgumentParser(); p.add_argument('ground_truth_csv'); p.add_argument('predictions_csv'); a=p.parse_args()
def load(path, key):
 with open(path,newline='',encoding='utf-8-sig') as f: return {int(r['frame_index']):int(r[key]) for r in csv.DictReader(f) if r.get(key, '').strip()}
gt=load(a.ground_truth_csv,'ground_truth_count'); pred=load(a.predictions_csv,'detections'); keys=sorted(set(gt)&set(pred))
if not keys: raise SystemExit('No overlapping frame_index values found.')
errors=[pred[k]-gt[k] for k in keys]
print(json.dumps({'frames_compared':len(keys),'mae':round(sum(abs(x) for x in errors)/len(errors),4),'rmse':round(math.sqrt(sum(x*x for x in errors)/len(errors)),4),'bias_pred_minus_truth':round(sum(errors)/len(errors),4),'warning':'Count metrics only; box-level precision/recall requires manually labeled bounding boxes.'},indent=2))
