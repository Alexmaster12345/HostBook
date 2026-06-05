from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from app.database import get_db
from app.models import Asset, Reservation, HostMetric, ReservationStatus, User
from app.schemas import UtilizationReport
from app.auth import get_current_user

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/utilization", response_model=List[UtilizationReport])
def utilization_report(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    assets = db.query(Asset).all()
    report = []
    for asset in assets:
        reservations = db.query(Reservation).filter(
            Reservation.asset_id == asset.id,
            Reservation.status.in_([ReservationStatus.active, ReservationStatus.expired]),
        ).all()

        total_hours = sum(
            (r.ends_at - r.starts_at).total_seconds() / 3600
            for r in reservations
        )

        avg_cpu = db.query(func.avg(HostMetric.cpu_percent)).filter(
            HostMetric.asset_id == asset.id
        ).scalar()

        avg_ram = db.query(func.avg(HostMetric.ram_percent)).filter(
            HostMetric.asset_id == asset.id
        ).scalar()

        report.append(UtilizationReport(
            asset_id=asset.id,
            hostname=asset.hostname,
            total_reservations=len(reservations),
            total_hours_reserved=round(total_hours, 2),
            avg_cpu=round(avg_cpu, 1) if avg_cpu else None,
            avg_ram=round(avg_ram, 1) if avg_ram else None,
        ))

    return sorted(report, key=lambda x: x.total_hours_reserved, reverse=True)


@router.get("/idle")
def idle_hosts(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    from app.models import AssetStatus
    from datetime import datetime, timedelta

    cutoff = datetime.utcnow() - timedelta(hours=24)
    idle = []
    for asset in db.query(Asset).filter(Asset.status == AssetStatus.available).all():
        last_metric = (
            db.query(HostMetric)
            .filter(HostMetric.asset_id == asset.id)
            .order_by(HostMetric.recorded_at.desc())
            .first()
        )
        if not last_metric or last_metric.recorded_at < cutoff:
            idle.append({"asset_id": asset.id, "hostname": asset.hostname, "last_seen": last_metric.recorded_at if last_metric else None})

    return idle


@router.get("/summary")
def summary(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    from app.models import AssetStatus
    total    = db.query(Asset).count()
    available = db.query(Asset).filter(Asset.status == AssetStatus.available).count()
    reserved  = db.query(Asset).filter(Asset.status == AssetStatus.reserved).count()
    in_use    = db.query(Asset).filter(Asset.status == AssetStatus.in_use).count()
    offline   = db.query(Asset).filter(Asset.status == AssetStatus.offline).count()
    maintenance = db.query(Asset).filter(Asset.status == AssetStatus.maintenance).count()
    return {
        "total": total,
        "available": available,
        "reserved": reserved,
        "in_use": in_use,
        "offline": offline,
        "maintenance": maintenance,
    }
