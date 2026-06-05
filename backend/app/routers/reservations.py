from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import Reservation, Asset, ReservationStatus, User
from app.schemas import ReservationCreate, ReservationOut
from app.auth import get_current_user
from app import logic

router = APIRouter(prefix="/api/v1/reservations", tags=["reservations"])


@router.get("/", response_model=List[ReservationOut])
def list_reservations(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    logic.expire_past_reservations(db)
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
def create_reservation(payload: ReservationCreate, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    asset = db.query(Asset).filter(Asset.id == payload.asset_id).first()
    if not asset:
        raise HTTPException(404, "Asset not found")

    return logic.create_reservation(
        db=db,
        asset=asset,
        user_id=current_user.id,
        reservation_type=payload.reservation_type,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        purpose=payload.purpose,
    )


@router.delete("/{reservation_id}", status_code=204)
def cancel_reservation(reservation_id: int, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    r = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not r:
        raise HTTPException(404, "Reservation not found")
    is_admin = current_user.role in ("admin", "infra_engineer")
    logic.cancel_reservation(db, r, current_user.id, is_admin)


@router.post("/expire", status_code=200, tags=["admin"])
def expire_reservations(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    count = logic.expire_past_reservations(db)
    return {"expired": count}


@router.get("/{reservation_id}/remaining")
def time_remaining(reservation_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    r = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not r:
        raise HTTPException(404, "Reservation not found")
    return {"reservation_id": reservation_id, "remaining": logic.time_remaining(r)}


@router.get("/asset/{asset_id}/who", tags=["assets"])
def who_has_asset(asset_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    r = logic.who_has(db, asset_id)
    if not r:
        return {"asset_id": asset_id, "reserved": False}
    return {
        "asset_id":   asset_id,
        "reserved":   True,
        "user":       r.user.username if r.user else None,
        "purpose":    r.purpose,
        "starts_at":  r.starts_at,
        "ends_at":    r.ends_at,
        "remaining":  logic.time_remaining(r),
        "status":     r.status,
    }
