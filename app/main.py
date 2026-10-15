"""PoultryGuard FastAPI Application
Complete REST API for Farms, Flocks, Video Analytics, Spatial High-Density Screening,
Health Events, Automated Triage Alerts, SMS Notifications, Model Evaluation, and Reports.
"""
from __future__ import annotations

import csv
import datetime
import io
import json
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException, Query, Response, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from . import db
from .schemas import (
    FarmCreate,
    FarmUpdate,
    FlockCreate,
    FlockUpdate,
    HealthEventCreate,
    AlertUpdate,
    DensityEventUpdate,
    DensitySettingsUpdate,
    SMSTestRequest
)
from .risk import assess_event
from .analysis import analyze_video, get_detector, get_active_density_config
from .density import DensityConfig
from .sms import (
    get_sms_provider,
    dispatch_alert_sms,
    format_sms_message,
    normalize_phone_number,
    mask_phone_number
)

settings = get_settings()
db.init_db()

app = FastAPI(
    title=settings.app_name,
    version="1.2.0",
    description="PoultryGuard Early Warning & Flock Monitoring System. Computer-vision analytics, spatial density screening, behavioral indicators, and operational alerts for smallholder poultry coops."
)

# Enable CORS for local frontend dev server & production builds
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# System Endpoints
# ---------------------------------------------------------------------------

@app.get('/health', tags=["System"])
def health():
    return {
        "status": "ok",
        "service": settings.app_name,
        "timestamp": time.time()
    }

@app.get('/api/v1/status', tags=["System"])
def system_status():
    db_ok = False
    try:
        with db.connect() as c:
            c.execute('SELECT 1')
        db_ok = True
    except Exception:
        db_ok = False

    detector = get_detector()
    is_custom = bool(settings.custom_model_path.strip())

    sms_provider = get_sms_provider()
    sms_ready, sms_reason = sms_provider.is_configured()

    density_cfg = get_active_density_config()

    return {
        "api": "ok",
        "database": "ok" if db_ok else "error",
        "detector_model": detector.model_path,
        "detector_device": detector.device,
        "is_custom_model": is_custom,
        "detection_scope": (
            "Custom poultry weights" if is_custom 
            else "Generic COCO bird proxy (detections are screening indicators, not confirmed headcounts)"
        ),
        "frame_stride": settings.frame_stride,
        "detection_confidence_threshold": settings.detect_conf,
        "max_upload_mb": settings.max_upload_mb,
        "model_error": detector.model_error,
        "density_screening": {
            "grid_layout": density_cfg.layout_name,
            "count_threshold": density_cfg.count_threshold,
            "persistence_frames": density_cfg.persistence_frames
        },
        "sms_status": {
            "enabled": os.getenv("SMS_ENABLED", "false").lower() in ("true", "1", "yes"),
            "provider": sms_provider.name,
            "ready": sms_ready,
            "message": sms_reason,
            "recipient_masked": mask_phone_number(os.getenv("SMS_RECIPIENT", "7530088644"))
        },
        "note": "Alerts and detections are screening guidance for human review, not veterinary diagnosis."
    }

# ---------------------------------------------------------------------------
# Farms Endpoints (with idempotency / de-duplication)
# ---------------------------------------------------------------------------

@app.post('/api/v1/farms', status_code=201, tags=["Farms"])
def create_farm(payload: FarmCreate):
    clean_name = payload.name.strip()
    existing = db.one('SELECT * FROM farms WHERE LOWER(name)=LOWER(?)', (clean_name,))
    if existing:
        db.execute(
            'UPDATE farms SET location=?, contact_name=?, contact_phone=?, notes=?, updated_at=CURRENT_TIMESTAMP WHERE id=?',
            (payload.location, payload.contact_name, payload.contact_phone, payload.notes, existing['id'])
        )
        return db.one('SELECT * FROM farms WHERE id=?', (existing['id'],))

    fid = db.execute(
        'INSERT INTO farms(name, location, contact_name, contact_phone, notes) VALUES(?,?,?,?,?)',
        (clean_name, payload.location, payload.contact_name, payload.contact_phone, payload.notes)
    )
    return db.one('SELECT * FROM farms WHERE id=?', (fid,))

@app.get('/api/v1/farms', tags=["Farms"])
def list_farms():
    farms = db.rows('SELECT * FROM farms ORDER BY id DESC')
    for f in farms:
        f['flock_count'] = db.one('SELECT COUNT(*) n FROM flocks WHERE farm_id=?', (f['id'],))['n']
    return farms

@app.get('/api/v1/farms/{farm_id}', tags=["Farms"])
def get_farm(farm_id: int):
    farm = db.one('SELECT * FROM farms WHERE id=?', (farm_id,))
    if not farm:
        raise HTTPException(404, 'Farm not found')
    farm['flocks'] = db.rows('SELECT * FROM flocks WHERE farm_id=? ORDER BY id DESC', (farm_id,))
    return farm

@app.put('/api/v1/farms/{farm_id}', tags=["Farms"])
@app.patch('/api/v1/farms/{farm_id}', tags=["Farms"])
def update_farm(farm_id: int, payload: FarmUpdate):
    farm = db.one('SELECT * FROM farms WHERE id=?', (farm_id,))
    if not farm:
        raise HTTPException(404, 'Farm not found')
    
    updates = []
    args = []
    if payload.name is not None:
        updates.append("name=?")
        args.append(payload.name.strip())
    if payload.location is not None:
        updates.append("location=?")
        args.append(payload.location)
    if payload.contact_name is not None:
        updates.append("contact_name=?")
        args.append(payload.contact_name)
    if payload.contact_phone is not None:
        updates.append("contact_phone=?")
        args.append(payload.contact_phone)
    if payload.notes is not None:
        updates.append("notes=?")
        args.append(payload.notes)

    if updates:
        updates.append("updated_at=CURRENT_TIMESTAMP")
        args.append(farm_id)
        db.execute(f"UPDATE farms SET {', '.join(updates)} WHERE id=?", tuple(args))
    
    return db.one('SELECT * FROM farms WHERE id=?', (farm_id,))

@app.delete('/api/v1/farms/{farm_id}', tags=["Farms"])
def delete_farm(farm_id: int):
    farm = db.one('SELECT * FROM farms WHERE id=?', (farm_id,))
    if not farm:
        raise HTTPException(404, 'Farm not found')
    db.execute('DELETE FROM farms WHERE id=?', (farm_id,))
    return {"message": "Farm deleted successfully", "id": farm_id}

# ---------------------------------------------------------------------------
# Flocks Endpoints (with de-duplication per farm)
# ---------------------------------------------------------------------------

@app.post('/api/v1/flocks', status_code=201, tags=["Flocks"])
def create_flock(payload: FlockCreate):
    if payload.farm_id is not None:
        if not db.one('SELECT id FROM farms WHERE id=?', (payload.farm_id,)):
            raise HTTPException(404, f'Farm with ID {payload.farm_id} not found')
    
    clean_name = payload.name.strip()
    # Check for existing duplicate flock under this farm
    if payload.farm_id is not None:
        existing = db.one('SELECT * FROM flocks WHERE farm_id=? AND LOWER(name)=LOWER(?)', (payload.farm_id, clean_name))
        if existing:
            db.execute(
                'UPDATE flocks SET breed=?, bird_count=?, age_days=?, housing_type=?, status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?',
                (payload.breed, payload.bird_count or 0, payload.age_days or 0, payload.housing_type, payload.status or 'active', existing['id'])
            )
            return db.one('SELECT * FROM flocks WHERE id=?', (existing['id'],))

    fid = db.execute(
        'INSERT INTO flocks(farm_id, name, breed, bird_count, age_days, housing_type, status) VALUES(?,?,?,?,?,?,?)',
        (payload.farm_id, clean_name, payload.breed, payload.bird_count or 0, payload.age_days or 0, payload.housing_type, payload.status or 'active')
    )
    return db.one('SELECT * FROM flocks WHERE id=?', (fid,))

@app.get('/api/v1/flocks', tags=["Flocks"])
def list_flocks(farm_id: Optional[int] = None):
    if farm_id is not None:
        flocks = db.rows('SELECT f.*, fm.name as farm_name FROM flocks f LEFT JOIN farms fm ON f.farm_id=fm.id WHERE f.farm_id=? ORDER BY f.id DESC', (farm_id,))
    else:
        flocks = db.rows('SELECT f.*, fm.name as farm_name FROM flocks f LEFT JOIN farms fm ON f.farm_id=fm.id ORDER BY f.id DESC')
    return flocks

@app.get('/api/v1/flocks/{flock_id}', tags=["Flocks"])
def get_flock(flock_id: int):
    flock = db.one('SELECT f.*, fm.name as farm_name FROM flocks f LEFT JOIN farms fm ON f.farm_id=fm.id WHERE f.id=?', (flock_id,))
    if not flock:
        raise HTTPException(404, 'Flock not found')
    flock['recent_events'] = db.rows('SELECT * FROM health_events WHERE flock_id=? ORDER BY reported_at DESC LIMIT 10', (flock_id,))
    flock['recent_jobs'] = db.rows('SELECT id, original_name, status, created_at, result_json FROM jobs WHERE flock_id=? ORDER BY created_at DESC LIMIT 5', (flock_id,))
    flock['density_events'] = db.rows('SELECT * FROM density_events WHERE flock_id=? ORDER BY created_at DESC LIMIT 10', (flock_id,))
    return flock

@app.put('/api/v1/flocks/{flock_id}', tags=["Flocks"])
@app.patch('/api/v1/flocks/{flock_id}', tags=["Flocks"])
def update_flock(flock_id: int, payload: FlockUpdate):
    flock = db.one('SELECT * FROM flocks WHERE id=?', (flock_id,))
    if not flock:
        raise HTTPException(404, 'Flock not found')
    
    updates = []
    args = []
    if payload.name is not None:
        updates.append("name=?")
        args.append(payload.name.strip())
    if payload.breed is not None:
        updates.append("breed=?")
        args.append(payload.breed)
    if payload.bird_count is not None:
        updates.append("bird_count=?")
        args.append(payload.bird_count)
    if payload.age_days is not None:
        updates.append("age_days=?")
        args.append(payload.age_days)
    if payload.housing_type is not None:
        updates.append("housing_type=?")
        args.append(payload.housing_type)
    if payload.status is not None:
        updates.append("status=?")
        args.append(payload.status)

    if updates:
        updates.append("updated_at=CURRENT_TIMESTAMP")
        args.append(flock_id)
        db.execute(f"UPDATE flocks SET {', '.join(updates)} WHERE id=?", tuple(args))
    
    return db.one('SELECT * FROM flocks WHERE id=?', (flock_id,))

@app.delete('/api/v1/flocks/{flock_id}', tags=["Flocks"])
def delete_flock(flock_id: int):
    flock = db.one('SELECT * FROM flocks WHERE id=?', (flock_id,))
    if not flock:
        raise HTTPException(404, 'Flock not found')
    db.execute('DELETE FROM flocks WHERE id=?', (flock_id,))
    return {"message": "Flock deleted successfully", "id": flock_id}

# ---------------------------------------------------------------------------
# Health Events Endpoints (with automated Urgent SMS)
# ---------------------------------------------------------------------------

@app.post('/api/v1/health-events', status_code=201, tags=["Health Events"])
def create_event(payload: HealthEventCreate):
    farm_name = "Farm"
    flock_name = "Flock"
    if payload.farm_id is not None:
        f = db.one('SELECT id, name FROM farms WHERE id=?', (payload.farm_id,))
        if not f:
            raise HTTPException(404, f'Farm with ID {payload.farm_id} not found')
        farm_name = f['name']
    if payload.flock_id is not None:
        fl = db.one('SELECT id, name FROM flocks WHERE id=?', (payload.flock_id,))
        if not fl:
            raise HTTPException(404, f'Flock with ID {payload.flock_id} not found')
        flock_name = fl['name']

    risk = assess_event(
        signs=payload.signs,
        sick_count=payload.sick_count,
        deaths=payload.deaths,
        feed_change=payload.feed_change,
        water_change=payload.water_change
    )

    eid = db.execute(
        '''INSERT INTO health_events
           (farm_id, flock_id, event_date, signs, sick_count, deaths, feed_change, water_change, notes, risk_level)
           VALUES(?,?,?,?,?,?,?,?,?,?)''',
        (
            payload.farm_id,
            payload.flock_id,
            payload.event_date,
            json.dumps(payload.signs),
            payload.sick_count,
            payload.deaths,
            payload.feed_change,
            payload.water_change,
            payload.notes,
            risk['risk_level']
        )
    )

    # Automatically generate an alert if risk is above routine
    if risk['risk_level'] != 'routine':
        title = f"Health Warning: {flock_name} ({risk['risk_level'].upper()})"
        cur = db.execute(
            'INSERT INTO alerts(farm_id, flock_id, severity, title, message, alert_type) VALUES(?,?,?,?,?, "health_review")',
            (payload.farm_id, payload.flock_id, risk['risk_level'], title, risk['advice'])
        )
        aid = cur

        # If URGENT risk (multiple deaths or severe respiratory), dispatch SMS
        if risk['risk_level'] == 'urgent':
            details = f"{payload.sick_count} sick birds, {payload.deaths} deaths reported"
            sms_text = format_sms_message(
                category="urgent_health",
                farm_name=farm_name,
                flock_name=flock_name,
                details=details,
                alert_id=aid
            )
            dispatch_alert_sms("urgent_health", sms_text, alert_id=aid)

    res = db.one('SELECT * FROM health_events WHERE id=?', (eid,))
    res['signs'] = json.loads(res['signs']) if res['signs'] else []
    return {**res, **risk}

@app.get('/api/v1/health-events', tags=["Health Events"])
def list_events(farm_id: Optional[int] = None, flock_id: Optional[int] = None):
    query = '''SELECT h.*, f.name as farm_name, fl.name as flock_name 
               FROM health_events h
               LEFT JOIN farms f ON h.farm_id = f.id
               LEFT JOIN flocks fl ON h.flock_id = fl.id'''
    args = []
    conditions = []
    if farm_id is not None:
        conditions.append("h.farm_id=?")
        args.append(farm_id)
    if flock_id is not None:
        conditions.append("h.flock_id=?")
        args.append(flock_id)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY h.reported_at DESC"
    
    events = db.rows(query, tuple(args))
    for e in events:
        try:
            e['signs'] = json.loads(e['signs']) if e['signs'] else []
        except Exception:
            e['signs'] = []
    return events

# ---------------------------------------------------------------------------
# Video Jobs & Analysis Endpoints
# ---------------------------------------------------------------------------

def _run_video_job(jid: str, video_path: str):
    """Background worker for video processing."""
    try:
        analyze_video(jid, video_path)
    except Exception as exc:
        err_msg = str(exc)
        with db.connect() as c:
            c.execute(
                "UPDATE jobs SET status='failed', finished_at=CURRENT_TIMESTAMP, error=? WHERE id=?",
                (err_msg, jid)
            )
            c.execute(
                'INSERT INTO alerts(job_id, severity, title, message, alert_type) VALUES(?,?,?,?, "system_quality")',
                (jid, 'review', 'Video Analysis Processing Failed', err_msg[:500])
            )

@app.post('/api/v1/videos', status_code=202, tags=["Video Analysis"])
def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    farm_id: Optional[int] = Form(None),
    flock_id: Optional[int] = Form(None)
):
    allowed_exts = {'.mp4', '.avi', '.mov', '.mkv', '.m4v'}
    filename = file.filename or 'video.mp4'
    suffix = Path(filename).suffix.lower()
    
    if suffix not in allowed_exts:
        raise HTTPException(
            415,
            f"Unsupported video format '{suffix}'. Supported formats: MP4, AVI, MOV, MKV, M4V."
        )

    jid = uuid.uuid4().hex
    dest = settings.storage_dir / 'uploads' / f"{jid}{suffix}"
    total_bytes = 0
    max_bytes = settings.max_upload_mb * 1024 * 1024

    try:
        with dest.open('wb') as out_f:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    out_f.close()
                    dest.unlink(missing_ok=True)
                    raise HTTPException(413, f"Video exceeds {settings.max_upload_mb} MB limit.")
                out_f.write(chunk)
    finally:
        file.file.close()

    # Create job in database
    db.execute(
        '''INSERT INTO jobs (id, farm_id, flock_id, original_name, video_path, status, progress_percent)
           VALUES (?, ?, ?, ?, ?, 'queued', 0.0)''',
        (jid, farm_id, flock_id, Path(filename).name, str(dest.resolve()))
    )

    # Dispatch asynchronous background task
    background_tasks.add_task(_run_video_job, jid, str(dest))

    return {
        "id": jid,
        "job_id": jid,
        "status": "queued",
        "original_name": Path(filename).name,
        "bytes": total_bytes,
        "status_url": f"/api/v1/jobs/{jid}"
    }

@app.get('/api/v1/jobs', tags=["Video Analysis"])
def list_jobs(limit: int = Query(50, ge=1, le=200)):
    jobs = db.rows(
        '''SELECT j.id, j.farm_id, j.flock_id, j.original_name, j.status, j.progress_percent,
                  j.created_at, j.started_at, j.finished_at, j.error, j.result_json, j.density_config_json,
                  f.name as farm_name, fl.name as flock_name
           FROM jobs j
           LEFT JOIN farms f ON j.farm_id = f.id
           LEFT JOIN flocks fl ON j.flock_id = fl.id
           ORDER BY j.created_at DESC LIMIT ?''',
        (limit,)
    )
    for j in jobs:
        try:
            j['result_json'] = json.loads(j['result_json']) if j['result_json'] else None
        except Exception:
            j['result_json'] = None
        try:
            j['density_config_json'] = json.loads(j['density_config_json']) if j['density_config_json'] else None
        except Exception:
            j['density_config_json'] = None
    return jobs

@app.get('/api/v1/jobs/{jid}', tags=["Video Analysis"])
def get_job(jid: str):
    job = db.one(
        '''SELECT j.*, f.name as farm_name, fl.name as flock_name
           FROM jobs j
           LEFT JOIN farms f ON j.farm_id = f.id
           LEFT JOIN flocks fl ON j.flock_id = fl.id
           WHERE j.id=?''',
        (jid,)
    )
    if not job:
        raise HTTPException(404, 'Job not found')
    try:
        job['metadata_json'] = json.loads(job['metadata_json']) if job['metadata_json'] else None
    except Exception:
        job['metadata_json'] = None
    try:
        job['result_json'] = json.loads(job['result_json']) if job['result_json'] else None
    except Exception:
        job['result_json'] = None
    try:
        job['density_config_json'] = json.loads(job['density_config_json']) if job['density_config_json'] else None
    except Exception:
        job['density_config_json'] = None
    return job

@app.get('/api/v1/jobs/{jid}/observations', tags=["Video Analysis"])
def get_job_observations(jid: str):
    if not db.one('SELECT id FROM jobs WHERE id=?', (jid,)):
        raise HTTPException(404, 'Job not found')
    
    rows = db.rows(
        '''SELECT frame_index, timestamp_sec, detections, track_ids_json, boxes_json, motion_ratio, density_score 
           FROM observations WHERE job_id=? ORDER BY frame_index''',
        (jid,)
    )
    for r in rows:
        try:
            r['track_ids'] = json.loads(r.pop('track_ids_json', '[]'))
        except Exception:
            r['track_ids'] = []
        try:
            r['boxes'] = json.loads(r.pop('boxes_json', '[]'))
        except Exception:
            r['boxes'] = []
    return rows

@app.get('/api/v1/jobs/{jid}/observations.csv', tags=["Video Analysis"])
def download_observations_csv(jid: str):
    csv_file = settings.storage_dir / 'jobs' / jid / 'observations.csv'
    if not csv_file.exists():
        job = db.one('SELECT status, error FROM jobs WHERE id=?', (jid,))
        if not job:
            raise HTTPException(404, 'Job not found')
        raise HTTPException(409, f"Observations CSV not ready (job status: {job['status']})")
    return FileResponse(
        csv_file,
        media_type='text/csv',
        filename=f"poultryguard_{jid}_observations.csv"
    )

@app.get('/api/v1/jobs/{jid}/summary', tags=["Video Analysis"])
def get_job_summary(jid: str):
    summary_file = settings.storage_dir / 'jobs' / jid / 'summary.json'
    if not summary_file.exists():
        job = db.one('SELECT status, error FROM jobs WHERE id=?', (jid,))
        if not job:
            raise HTTPException(404, 'Job not found')
        raise HTTPException(409, f"Summary not available (status: {job['status']})")
    return json.loads(summary_file.read_text(encoding='utf-8'))

@app.get('/api/v1/jobs/{jid}/video', tags=["Video Analysis"])
def get_job_video(jid: str):
    job = db.one('SELECT id, status FROM jobs WHERE id=?', (jid,))
    if not job:
        raise HTTPException(404, 'Job not found')
    p = settings.storage_dir / 'jobs' / jid / 'annotated.mp4'
    if not p.exists():
        raise HTTPException(409, 'Annotated video is not available yet; check job status.')
    return FileResponse(
        p,
        media_type='video/mp4',
        filename=f"poultryguard_{jid}_annotated.mp4"
    )

@app.get('/api/v1/jobs/{jid}/frames', tags=["Video Analysis"])
def list_job_frames(jid: str):
    fdir = settings.storage_dir / 'frames' / jid
    if not fdir.exists():
        return []
    frame_files = sorted(f.name for f in fdir.glob("frame_*.jpg"))
    return frame_files

@app.get('/api/v1/jobs/{jid}/frames/{frame_name}', tags=["Video Analysis"])
def get_job_frame(jid: str, frame_name: str):
    clean_name = Path(frame_name).name
    if clean_name != frame_name:
        raise HTTPException(400, 'Invalid frame name')
    p = settings.storage_dir / 'frames' / jid / clean_name
    if not p.exists():
        raise HTTPException(404, 'Frame not found')
    return FileResponse(p, media_type='image/jpeg')

# ---------------------------------------------------------------------------
# Spatial Density Events Endpoints
# ---------------------------------------------------------------------------

@app.get('/api/v1/density-events', tags=["Density Events"])
def list_density_events(
    job_id: Optional[str] = Query(None),
    farm_id: Optional[int] = Query(None),
    flock_id: Optional[int] = Query(None),
    review_status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500)
):
    query = """
        SELECT de.*, f.name as farm_name, fl.name as flock_name, j.original_name as video_name
        FROM density_events de
        LEFT JOIN farms f ON de.farm_id = f.id
        LEFT JOIN flocks fl ON de.flock_id = fl.id
        LEFT JOIN jobs j ON de.job_id = j.id
    """
    conds = []
    args = []
    if job_id:
        conds.append("de.job_id=?")
        args.append(job_id)
    if farm_id is not None:
        conds.append("de.farm_id=?")
        args.append(farm_id)
    if flock_id is not None:
        conds.append("de.flock_id=?")
        args.append(flock_id)
    if review_status:
        conds.append("de.review_status=?")
        args.append(review_status)

    if conds:
        query += " WHERE " + " AND ".join(conds)
    query += " ORDER BY de.created_at DESC LIMIT ?"
    args.append(limit)

    return db.rows(query, tuple(args))

@app.get('/api/v1/jobs/{jid}/density-events', tags=["Density Events"])
def get_job_density_events(jid: str):
    if not db.one('SELECT id FROM jobs WHERE id=?', (jid,)):
        raise HTTPException(404, 'Job not found')
    return db.rows(
        "SELECT * FROM density_events WHERE job_id=? ORDER BY frame_index ASC",
        (jid,)
    )

@app.get('/api/v1/jobs/{jid}/density-events/{eid}/image', tags=["Density Events"])
def get_density_evidence_image(jid: str, eid: str, type: str = Query("annotated", pattern="^(annotated|original)$")):
    event = db.one("SELECT * FROM density_events WHERE id=? AND job_id=?", (eid, jid))
    if not event:
        raise HTTPException(404, "Density event not found for this job")

    filename = f"{eid}_{type}.jpg"
    img_path = settings.storage_dir / "jobs" / jid / "density_events" / filename
    if not img_path.exists():
        raise HTTPException(404, f"Evidence image '{filename}' not found on storage")

    return FileResponse(img_path, media_type="image/jpeg", filename=filename)

@app.patch('/api/v1/density-events/{eid}', tags=["Density Events"])
def update_density_event_status(eid: str, payload: DensityEventUpdate):
    event = db.one("SELECT * FROM density_events WHERE id=?", (eid,))
    if not event:
        raise HTTPException(404, "Density event not found")

    notes = payload.notes if payload.notes is not None else event.get("notes", "")
    db.execute(
        "UPDATE density_events SET review_status=?, notes=? WHERE id=?",
        (payload.review_status, notes, eid)
    )
    return db.one("SELECT * FROM density_events WHERE id=?", (eid,))

# ---------------------------------------------------------------------------
# Alerts Endpoints
# ---------------------------------------------------------------------------

@app.get('/api/v1/alerts', tags=["Alerts"])
def list_alerts(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    alert_type: Optional[str] = Query(None)
):
    query = '''SELECT a.*, f.name as farm_name, fl.name as flock_name
               FROM alerts a
               LEFT JOIN farms f ON a.farm_id = f.id
               LEFT JOIN flocks fl ON a.flock_id = fl.id'''
    args = []
    conds = []
    if status and status != 'all':
        conds.append("a.status=?")
        args.append(status)
    if severity and severity != 'all':
        conds.append("a.severity=?")
        args.append(severity)
    if alert_type and alert_type != 'all':
        conds.append("a.alert_type=?")
        args.append(alert_type)
    if conds:
        query += " WHERE " + " AND ".join(conds)
    query += " ORDER BY a.created_at DESC"
    return db.rows(query, tuple(args))

@app.patch('/api/v1/alerts/{aid}', tags=["Alerts"])
def update_alert(aid: int, payload: AlertUpdate):
    if payload.status not in {'open', 'acknowledged', 'resolved'}:
        raise HTTPException(422, "status must be one of: 'open', 'acknowledged', 'resolved'")
    alert = db.one('SELECT * FROM alerts WHERE id=?', (aid,))
    if not alert:
        raise HTTPException(404, 'Alert not found')

    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    created_at_str = alert.get('created_at')

    if payload.status == 'acknowledged':
        db.execute(
            'UPDATE alerts SET status=?, acknowledged_at=? WHERE id=?',
            (payload.status, now, aid)
        )
    elif payload.status == 'resolved':
        resp_sec = None
        if created_at_str:
            try:
                dt_c = datetime.datetime.fromisoformat(created_at_str.replace("Z", ""))
                if dt_c.tzinfo is None:
                    dt_c = dt_c.replace(tzinfo=datetime.timezone.utc)
                dt_now = datetime.datetime.now(datetime.timezone.utc)
                resp_sec = max(0.0, round((dt_now - dt_c).total_seconds(), 1))
            except Exception:
                pass
        db.execute(
            'UPDATE alerts SET status=?, resolved_at=?, response_time_sec=?, dismiss_reason=? WHERE id=?',
            (payload.status, now, resp_sec, payload.dismiss_reason or '', aid)
        )
    else:
        db.execute('UPDATE alerts SET status=? WHERE id=?', (payload.status, aid))

    return db.one('SELECT * FROM alerts WHERE id=?', (aid,))

@app.post('/api/v1/alerts/{aid}/acknowledge', tags=["Alerts"])
def acknowledge_alert(aid: int):
    return update_alert(aid, AlertUpdate(status='acknowledged'))

@app.post('/api/v1/alerts/{aid}/resolve', tags=["Alerts"])
def resolve_alert(aid: int, dismiss_reason: str = Body(default="", embed=True)):
    return update_alert(aid, AlertUpdate(status='resolved', dismiss_reason=dismiss_reason))

# ---------------------------------------------------------------------------
# SMS Notifications & Provider Endpoints
# ---------------------------------------------------------------------------

@app.get('/api/v1/sms/status', tags=["SMS Notifications"])
def sms_status():
    sms_enabled = os.getenv("SMS_ENABLED", "false").lower() in ("true", "1", "yes")
    provider = get_sms_provider()
    ready, reason = provider.is_configured()
    raw_recipient = os.getenv("SMS_RECIPIENT", "7530088644")
    valid, norm_phone, err = normalize_phone_number(raw_recipient)

    return {
        "enabled": sms_enabled,
        "provider": provider.name,
        "recipient_configured": valid,
        "recipient_masked": mask_phone_number(norm_phone if valid else raw_recipient),
        "cooldown_seconds": int(os.getenv("SMS_COOLDOWN_SEC", "300")),
        "dry_run": os.getenv("SMS_DRY_RUN", "false").lower() in ("true", "1", "yes"),
        "ready": ready and valid,
        "status_message": reason if not ready else ("Configured and ready to send." if valid else f"Invalid recipient: {err}")
    }

@app.post('/api/v1/sms/test', tags=["SMS Notifications"])
def send_test_sms(payload: SMSTestRequest):
    recipient = payload.recipient or os.getenv("SMS_RECIPIENT", "7530088644")
    msg = payload.message or "PoultryGuard TEST: Operational SMS notification verified. Screening guidance system active."
    
    # Temporarily override recipient if provided
    old_env = os.environ.get("SMS_RECIPIENT")
    try:
        if payload.recipient:
            os.environ["SMS_RECIPIENT"] = payload.recipient
        result = dispatch_alert_sms("manual_test", msg, force_dry_run=bool(payload.dry_run))
    finally:
        if old_env is not None:
            os.environ["SMS_RECIPIENT"] = old_env

    return result.to_dict()

@app.get('/api/v1/sms/notifications', tags=["SMS Notifications"])
def list_sms_notifications(limit: int = Query(50, ge=1, le=200)):
    rows = db.rows(
        "SELECT * FROM notifications ORDER BY created_at DESC LIMIT ?",
        (limit,)
    )
    for r in rows:
        r["recipient"] = mask_phone_number(r.get("recipient", ""))
    return rows

# ---------------------------------------------------------------------------
# Settings Endpoints
# ---------------------------------------------------------------------------

@app.get('/api/v1/settings', tags=["Settings"])
def get_all_settings():
    density_cfg = get_active_density_config()
    sms_provider = get_sms_provider()
    ready, reason = sms_provider.is_configured()

    return {
        "density": density_cfg.to_dict(),
        "detection": {
            "model_path": settings.model_path,
            "custom_model_path": settings.custom_model_path,
            "detect_conf": settings.detect_conf,
            "image_size": settings.image_size,
            "frame_stride": settings.frame_stride
        },
        "sms": {
            "enabled": os.getenv("SMS_ENABLED", "false").lower() in ("true", "1", "yes"),
            "provider": sms_provider.name,
            "recipient_masked": mask_phone_number(os.getenv("SMS_RECIPIENT", "7530088644")),
            "cooldown_seconds": int(os.getenv("SMS_COOLDOWN_SEC", "300")),
            "dry_run": os.getenv("SMS_DRY_RUN", "false").lower() in ("true", "1", "yes"),
            "ready": ready,
            "reason": reason
        }
    }

@app.put('/api/v1/settings/density', tags=["Settings"])
def update_density_settings(payload: DensitySettingsUpdate):
    cfg_data = {
        "grid_rows": payload.grid_rows,
        "grid_cols": payload.grid_cols,
        "count_threshold": payload.count_threshold,
        "area_threshold_pct": payload.area_threshold_pct,
        "persistence_frames": payload.persistence_frames,
        "clearing_threshold": payload.clearing_threshold,
        "clearing_frames": payload.clearing_frames
    }
    with db.connect() as c:
        c.execute(
            "INSERT INTO app_settings(key, value, updated_at) VALUES('density_config', ?, CURRENT_TIMESTAMP) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP",
            (json.dumps(cfg_data),)
        )
    return {"message": "Density settings updated successfully", "density_config": cfg_data}

# ---------------------------------------------------------------------------
# Model Evaluation Endpoints
# ---------------------------------------------------------------------------

@app.get('/api/v1/evaluation/results', tags=["Evaluation"])
def get_evaluation_results():
    eval_file = settings.data_dir / "model_evaluation.json"
    if not eval_file.exists():
        return {
            "status": "unvalidated",
            "message": "Ground-truth evaluation not yet generated. Run scripts/evaluate_model.py or trigger POST /api/v1/evaluation/run.",
            "metrics": None
        }
    try:
        return json.loads(eval_file.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(500, f"Could not parse evaluation file: {exc}")

# ---------------------------------------------------------------------------
# Reports & Analytics Endpoints
# ---------------------------------------------------------------------------

@app.get('/api/v1/reports/summary', tags=["Reports"])
def report_summary():
    farms_count = db.one('SELECT COUNT(*) n FROM farms')['n']
    flocks_count = db.one('SELECT COUNT(*) n FROM flocks')['n']
    events_count = db.one('SELECT COUNT(*) n FROM health_events')['n']
    total_jobs = db.one('SELECT COUNT(*) n FROM jobs')['n']
    completed_jobs = db.one("SELECT COUNT(*) n FROM jobs WHERE status='completed'")['n']
    failed_jobs = db.one("SELECT COUNT(*) n FROM jobs WHERE status='failed'")['n']
    open_alerts = db.one("SELECT COUNT(*) n FROM alerts WHERE status='open'")['n']
    ack_alerts = db.one("SELECT COUNT(*) n FROM alerts WHERE status='acknowledged'")['n']
    resolved_alerts = db.one("SELECT COUNT(*) n FROM alerts WHERE status='resolved'")['n']
    density_events_count = db.one('SELECT COUNT(*) n FROM density_events')['n']
    notifications_count = db.one('SELECT COUNT(*) n FROM notifications')['n']

    # Mean detections across completed jobs
    recent_jobs = db.rows("SELECT result_json FROM jobs WHERE status='completed' ORDER BY finished_at DESC LIMIT 10")
    recent_means = []
    for rj in recent_jobs:
        try:
            res = json.loads(rj['result_json']) if rj['result_json'] else {}
            if 'mean_detections_per_frame' in res:
                recent_means.append(res['mean_detections_per_frame'])
        except Exception:
            pass

    avg_flock_detections = round(float(sum(recent_means) / len(recent_means)), 1) if recent_means else 0.0

    # Load real evaluation status if available
    eval_file = settings.data_dir / "model_evaluation.json"
    eval_status = "Unvalidated (proxy-only)"
    map_50_score = None
    if eval_file.exists():
        try:
            ev_data = json.loads(eval_file.read_text(encoding="utf-8"))
            if ev_data.get("status") == "success":
                eval_status = "Evaluated against ground truth"
                map_50_score = ev_data.get("metrics", {}).get("mAP_50")
        except Exception:
            pass

    return {
        "farms": farms_count,
        "flocks": flocks_count,
        "health_events": events_count,
        "total_jobs": total_jobs,
        "completed_jobs": completed_jobs,
        "failed_jobs": failed_jobs,
        "open_alerts": open_alerts,
        "acknowledged_alerts": ack_alerts,
        "resolved_alerts": resolved_alerts,
        "density_events": density_events_count,
        "notifications_logged": notifications_count,
        "recent_average_detections_per_frame": avg_flock_detections,
        "model_validation_status": eval_status,
        "mAP_50_score": map_50_score,
        "accuracy_disclaimer": "Detection averages represent visible COCO bird-class detections per frame. Real accuracy evaluated against ground truth shows low recall (flock screening proxy, not headcount)."
    }

@app.get('/api/v1/reports/alerts.csv', tags=["Reports"])
def alerts_csv():
    rows = db.rows('SELECT * FROM alerts ORDER BY created_at DESC')
    output = io.StringIO()
    fields = ['id', 'farm_id', 'flock_id', 'job_id', 'severity', 'title', 'message', 'alert_type', 'density_event_id', 'status', 'created_at', 'acknowledged_at', 'resolved_at', 'response_time_sec', 'dismiss_reason']
    w = csv.DictWriter(output, fieldnames=fields)
    w.writeheader()
    for r in rows:
        row_dict = {f: r.get(f) for f in fields}
        w.writerow(row_dict)
    return Response(
        output.getvalue(),
        media_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename="poultryguard_alerts.csv"'}
    )

@app.get('/api/v1/reports/density_events.csv', tags=["Reports"])
def density_events_csv():
    rows = db.rows('SELECT * FROM density_events ORDER BY created_at DESC')
    output = io.StringIO()
    fields = [
        'id', 'job_id', 'farm_id', 'flock_id', 'zone_id', 'grid_layout', 'frame_index',
        'timestamp_sec', 'detection_count', 'threshold', 'occupied_area_pct',
        'start_time_sec', 'end_time_sec', 'duration_sec', 'persistence_frames',
        'trigger_reason', 'review_status', 'created_at', 'notes'
    ]
    w = csv.DictWriter(output, fieldnames=fields)
    w.writeheader()
    for r in rows:
        row_dict = {f: r.get(f) for f in fields}
        w.writerow(row_dict)
    return Response(
        output.getvalue(),
        media_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename="poultryguard_density_events.csv"'}
    )

@app.get('/api/v1/reports/notifications.csv', tags=["Reports"])
def notifications_csv():
    rows = db.rows('SELECT * FROM notifications ORDER BY created_at DESC')
    output = io.StringIO()
    fields = ['id', 'alert_id', 'event_type', 'recipient', 'provider', 'message_text', 'status', 'provider_message_id', 'error_detail', 'retry_count', 'created_at']
    w = csv.DictWriter(output, fieldnames=fields)
    w.writeheader()
    for r in rows:
        r_copy = dict(r)
        r_copy['recipient'] = mask_phone_number(r_copy.get('recipient', ''))
        row_dict = {f: r_copy.get(f) for f in fields}
        w.writerow(row_dict)
    return Response(
        output.getvalue(),
        media_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename="poultryguard_notifications.csv"'}
    )

@app.get('/api/v1/reports/events.csv', tags=["Reports"])
def events_csv():
    rows = db.rows('SELECT * FROM health_events ORDER BY reported_at DESC')
    output = io.StringIO()
    fields = ['id', 'farm_id', 'flock_id', 'event_date', 'reported_at', 'signs', 'sick_count', 'deaths', 'feed_change', 'water_change', 'risk_level', 'status', 'notes']
    w = csv.DictWriter(output, fieldnames=fields)
    w.writeheader()
    for r in rows:
        row_dict = {f: r.get(f) for f in fields}
        w.writerow(row_dict)
    return Response(
        output.getvalue(),
        media_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename="poultryguard_health_events.csv"'}
    )

@app.get('/api/v1/reports/jobs.csv', tags=["Reports"])
def jobs_csv():
    jobs = db.rows('SELECT id, farm_id, flock_id, original_name, status, created_at, started_at, finished_at, error, result_json FROM jobs ORDER BY created_at DESC')
    output = io.StringIO()
    fields = [
        'id', 'farm_id', 'flock_id', 'original_name', 'status', 'created_at', 'finished_at',
        'video_duration_sec', 'total_video_frames', 'sampled_frames', 'mean_detections_per_frame',
        'max_detections', 'unique_tracks', 'mean_motion_ratio', 'mean_density_score', 'processing_fps'
    ]
    w = csv.DictWriter(output, fieldnames=fields)
    w.writeheader()
    for j in jobs:
        res = {}
        try:
            res = json.loads(j['result_json']) if j['result_json'] else {}
        except Exception:
            pass
        row = {
            'id': j['id'],
            'farm_id': j['farm_id'],
            'flock_id': j['flock_id'],
            'original_name': j['original_name'],
            'status': j['status'],
            'created_at': j['created_at'],
            'finished_at': j['finished_at'],
            'video_duration_sec': res.get('video_duration_sec'),
            'total_video_frames': res.get('total_video_frames'),
            'sampled_frames': res.get('sampled_frames'),
            'mean_detections_per_frame': res.get('mean_detections_per_frame'),
            'max_detections': res.get('max_detections_in_single_frame'),
            'unique_tracks': res.get('unique_track_identities_observed'),
            'mean_motion_ratio': res.get('mean_motion_ratio'),
            'mean_density_score': res.get('mean_density_score'),
            'processing_fps': res.get('processing_fps'),
        }
        w.writerow(row)
    return Response(
        output.getvalue(),
        media_type='text/csv',
        headers={'Content-Disposition': 'attachment; filename="poultryguard_jobs.csv"'}
    )

# ---------------------------------------------------------------------------
# Mount Built Frontend if Available
# ---------------------------------------------------------------------------
dist_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if dist_dir.exists() and (dist_dir / "index.html").exists():
    app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="frontend")
