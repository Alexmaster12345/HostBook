from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import List
import os

from app.database import get_db
from app.models import Asset, HostMetric, ActivityLog
from app.schemas import MetricIn, MetricOut, ActivityLogOut
from app import logic

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])

AGENT_TOKEN = os.environ.get("AGENT_TOKEN", "changeme-agent-secret")


def verify_agent(x_agent_token: str = Header(...)):
    if x_agent_token != AGENT_TOKEN:
        raise HTTPException(401, "Invalid agent token")


@router.post("/heartbeat", status_code=200)
def heartbeat(payload: MetricIn, db: Session = Depends(get_db), _=Depends(verify_agent)):
    asset = db.query(Asset).filter(Asset.hostname == payload.hostname).first()
    if not asset:
        asset = Asset(
            hostname=payload.hostname,
            os=payload.os,
            ip_address=payload.ip_address,
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)

    # Keep OS and IP up to date on every heartbeat
    if payload.os and asset.os != payload.os:
        asset.os = payload.os
    if payload.ip_address and asset.ip_address != payload.ip_address:
        asset.ip_address = payload.ip_address

    logic.apply_heartbeat(
        db=db,
        asset=asset,
        active_users=payload.active_users,
        logged_in_users=payload.logged_in_users,
        cpu=payload.cpu_percent,
        ram=payload.ram_percent,
        disk=payload.disk_percent,
        load=payload.load_avg,
    )
    return {"ack": True, "asset_id": asset.id, "status": asset.status, "registered": True}


@router.get("/metrics/{hostname}", response_model=List[MetricOut])
def get_metrics(hostname: str, limit: int = 60, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.hostname == hostname).first()
    if not asset:
        raise HTTPException(404, "Host not found")
    return (db.query(HostMetric)
              .filter(HostMetric.asset_id == asset.id)
              .order_by(HostMetric.recorded_at.desc())
              .limit(limit).all())


@router.get("/activity/{hostname}", response_model=List[ActivityLogOut])
def get_activity(hostname: str, limit: int = 100, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.hostname == hostname).first()
    if not asset:
        raise HTTPException(404, "Host not found")
    return (db.query(ActivityLog)
              .filter(ActivityLog.asset_id == asset.id)
              .order_by(ActivityLog.recorded_at.desc())
              .limit(limit).all())
