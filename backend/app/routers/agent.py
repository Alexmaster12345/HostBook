from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.database import get_db
from app.models import Asset, AssetStatus, ActivityLog, HostMetric
from app.schemas import MetricIn, MetricOut, ActivityLogOut

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])

AGENT_TOKEN = __import__("os").environ.get("AGENT_TOKEN", "changeme-agent-secret")


def verify_agent(token: str = __import__("fastapi").Header(..., alias="X-Agent-Token")):
    if token != AGENT_TOKEN:
        raise HTTPException(401, "Invalid agent token")


@router.post("/heartbeat", status_code=200)
def heartbeat(payload: MetricIn, db: Session = Depends(get_db), _=Depends(verify_agent)):
    asset = db.query(Asset).filter(Asset.hostname == payload.hostname).first()
    if not asset:
        raise HTTPException(404, f"Unknown host: {payload.hostname}")

    # Update asset status based on active users
    if asset.status not in (AssetStatus.reserved, AssetStatus.maintenance):
        asset.status = AssetStatus.in_use if payload.active_users > 0 else AssetStatus.available

    # Record metric snapshot
    metric = HostMetric(
        asset_id=asset.id,
        cpu_percent=payload.cpu_percent,
        ram_percent=payload.ram_percent,
        disk_percent=payload.disk_percent,
        active_users=payload.active_users,
        load_avg=payload.load_avg,
    )
    db.add(metric)

    # Log each logged-in user as an activity event if not already seen this cycle
    for username in payload.logged_in_users:
        log = ActivityLog(
            asset_id=asset.id,
            username=username,
            event="active_session",
            recorded_at=datetime.utcnow(),
        )
        db.add(log)

    db.commit()
    return {"ack": True, "asset_id": asset.id}


@router.get("/metrics/{hostname}", response_model=List[MetricOut])
def get_metrics(hostname: str, limit: int = 60, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.hostname == hostname).first()
    if not asset:
        raise HTTPException(404, "Host not found")
    return (
        db.query(HostMetric)
        .filter(HostMetric.asset_id == asset.id)
        .order_by(HostMetric.recorded_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/activity/{hostname}", response_model=List[ActivityLogOut])
def get_activity(hostname: str, limit: int = 100, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.hostname == hostname).first()
    if not asset:
        raise HTTPException(404, "Host not found")
    return (
        db.query(ActivityLog)
        .filter(ActivityLog.asset_id == asset.id)
        .order_by(ActivityLog.recorded_at.desc())
        .limit(limit)
        .all()
    )
