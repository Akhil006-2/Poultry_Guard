import argparse
import json
import sys
import uuid
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings
from app import db
from app.analysis import analyze_video

p = argparse.ArgumentParser(description='Analyze a poultry video with PoultryGuard CV pipeline')
p.add_argument('video', help='Path to an MP4/AVI/MOV/MKV video')
p.add_argument('--job-id', default=None)
p.add_argument('--farm-id', type=int, default=None)
p.add_argument('--flock-id', type=int, default=None)

a = p.parse_args()
video = Path(a.video).resolve()
if not video.is_file():
    raise SystemExit(f'Video file not found: {video}')

settings = get_settings()
db.init_db()
jid = a.job_id or uuid.uuid4().hex

with db.connect() as c:
    c.execute(
        'INSERT OR REPLACE INTO jobs(id, farm_id, flock_id, original_name, video_path, status, progress_percent) VALUES(?,?,?,?,?, "queued", 0.0)',
        (jid, a.farm_id, a.flock_id, video.name, str(video))
    )

try:
    result = analyze_video(jid, str(video))
    print("\n=== VIDEO ANALYSIS COMPLETE ===")
    print(json.dumps(result, indent=2))
except Exception as e:
    with db.connect() as c:
        c.execute("UPDATE jobs SET status='failed', error=? WHERE id=?", (str(e), jid))
    raise
