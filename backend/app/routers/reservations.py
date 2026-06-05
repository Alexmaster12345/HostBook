from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List
from datetime import datetime

from app.database import get_db
from app.models import Reservation, Asset, ReservationStatus, AssetStatus, User
from app.schemas import ReservationCreate, ReservationOut
from app.auth import get_current_user

router = APIRouter(prefix="/api/v1/reservations", tags=["reservations"])


def _conflict_exists(db: Session, asset_id: int, starts_at: datetime, ends_at: datetime, exclude_id: int = None) -> bool:
    q = db.query(Reservation).filter(
        Reservation.asset_id == asset_id,
        Reservation.status.in_([ReservationStatus.pending, ReservationStatus.active]),
        Reservation.starts_at < ends_at,
        Reservation.ends_at > starts_at,
    )
    if exclude_id:
        q = q.filter(Reservation.id != exclude_id)
    return q.first() is not None


@router.get("/", response_model=List[ReservationOut])
def list_reservations(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role in ("admin", "infra_engineer"):
        return db.query(Reservation).all()
    return db.query(Reservation).filter(Reservation.user_id == current_user.id).all()


@router.get("/{reservation_id}", response_model=ReservationOut)
def get_reservation(reservation_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    r = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not r:
        raise HTTPException(404, "Reservation not found")
    return r


@router.post("/", response_model=ReservationOut, status_code=201)
def create_reservation(payload: ReservationCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if payload.ends_at <= payload.starts_at:
        raise HTTPException(400, "ends_at must be after starts_at")

    asset = db.query(Asset).filter(Asset.id == payload.asset_id).first()
    if not asset:
        raise HTTPException(404, "Asset not found")
    if asset.status == AssetStatus.offline:
        raise HTTPException(409, "Asset is offline")
    if asset.status == AssetStatus.maintenance:
        raise HTTPException(409, "Asset is under maintenance")
    if _conflict_exists(db, payload.asset_id, payload.starts_at, payload.ends_at):
        raise HTTPException(409, "Time slot conflicts with an existing reservation")

    reservation = Reservation(
        asset_id=payload.asset_id,
        user_id=current_user.id,
        reservation_type=payload.reservation_type,
        purpose=payload.purpose,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        status=ReservationStatus.active if payload.starts_at <= datetime.utcnow() else ReservationStatus.pending,
    )
    db.add(reservation)
    asset.status = AssetStatus.reserved
    db.commit()
    db.refresh(reservation)
    return reservation


@router.delete("/{reservation_id}", status_code=204)
def cancel_reservation(reservation_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    r = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not r:
        raise HTTPException(404, "Reservation not found")
    if r.user_id != current_user.id and current_user.role not in ("admin", "infra_engineer"):
        raise HTTPException(403, "Not your reservation")
    r.status = ReservationStatus.cancelled
    asset = db.query(Asset).filter(Asset.id == r.asset_id).first()
    if asset:
        asset.status = AssetStatus.available
    db.commit()


@router.post("/expire", status_code=200, tags=["admin"])
def expire_reservations(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    now = datetime.utcnow()
    expired = db.query(Reservation).filter(
        Reservation.status == ReservationStatus.active,
        Reservation.ends_at < now,
    ).all()
    for r in expired:
        r.status = ReservationStatus.expired
        asset = db.query(Asset).filter(Asset.id == r.asset_id).first()
        if asset and asset.status == AssetStatus.reserved:
            asset.status = AssetStatus.available
    db.commit()
    return {"expired": len(expired)}
