"""
Core HostBook business logic.
All state transitions and rules live here — routers call these functions,
never manipulate models directly.
"""

from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models import (
    Asset, AssetStatus, Reservation, ReservationStatus,
    ReservationType, ActivityLog, HostMetric
)


# ── Reservation rules ─────────────────────────────────────────────────────────

def validate_window(starts_at: datetime, ends_at: datetime):
    """Raise if the time window is invalid."""
    now = datetime.utcnow()
    if ends_at <= starts_at:
        raise HTTPException(400, "ends_at must be after starts_at")
    if ends_at <= now:
        raise HTTPException(400, "Reservation window is already in the past")
    if starts_at < now.replace(second=0, microsecond=0):
        # Allow starts_at to be slightly in the past (clock skew)
        pass


def check_conflict(db: Session, asset_id: int, starts_at: datetime,
                   ends_at: datetime, exclude_id: int = None) -> Reservation | None:
    """Return the conflicting reservation if one exists, else None."""
    q = db.query(Reservation).filter(
        Reservation.asset_id == asset_id,
        Reservation.status.in_([ReservationStatus.pending, ReservationStatus.active]),
        Reservation.starts_at < ends_at,
        Reservation.ends_at   > starts_at,
    )
    if exclude_id:
        q = q.filter(Reservation.id != exclude_id)
    return q.first()


def assert_asset_bookable(asset: Asset):
    """Raise if the asset cannot accept a new reservation."""
    if asset.status == AssetStatus.offline:
        raise HTTPException(409, f"{asset.hostname} is offline")
    if asset.status == AssetStatus.maintenance:
        raise HTTPException(409, f"{asset.hostname} is under maintenance")


def initial_status(starts_at: datetime) -> ReservationStatus:
    return (ReservationStatus.active
            if starts_at <= datetime.utcnow()
            else ReservationStatus.pending)


# ── Create ────────────────────────────────────────────────────────────────────

def create_reservation(db: Session, asset: Asset, user_id: int,
                       reservation_type: ReservationType,
                       starts_at: datetime, ends_at: datetime,
                       purpose: str = None) -> Reservation:
    validate_window(starts_at, ends_at)
    assert_asset_bookable(asset)

    conflict = check_conflict(db, asset.id, starts_at, ends_at)
    if conflict:
        owner = conflict.user.username if conflict.user else "another user"
        raise HTTPException(
            409,
            f"{asset.hostname} is already reserved by '{owner}' "
            f"from {conflict.starts_at.strftime('%Y-%m-%d %H:%M')} "
            f"to {conflict.ends_at.strftime('%Y-%m-%d %H:%M')}"
        )

    status = initial_status(starts_at)
    reservation = Reservation(
        asset_id=asset.id,
        user_id=user_id,
        reservation_type=reservation_type,
        purpose=purpose,
        starts_at=starts_at,
        ends_at=ends_at,
        status=status,
    )
    db.add(reservation)

    # Mark asset reserved only if the window starts now
    if status == ReservationStatus.active:
        asset.status = AssetStatus.reserved

    db.commit()
    db.refresh(reservation)
    return reservation


# ── Cancel ────────────────────────────────────────────────────────────────────

def cancel_reservation(db: Session, reservation: Reservation, requestor_id: int, is_admin: bool):
    if not is_admin and reservation.user_id != requestor_id:
        raise HTTPException(403, "You can only cancel your own reservations")
    if reservation.status in (ReservationStatus.expired, ReservationStatus.cancelled):
        raise HTTPException(400, f"Reservation is already {reservation.status}")

    reservation.status = ReservationStatus.cancelled
    _maybe_free_asset(db, reservation.asset_id)
    db.commit()


# ── Expiry sweep ──────────────────────────────────────────────────────────────

def expire_past_reservations(db: Session) -> int:
    """
    Move past-due active/pending reservations to 'expired' and
    free their assets if no other active reservation holds them.
    Called automatically on every API startup and by the /expire endpoint.
    """
    now = datetime.utcnow()
    expired = db.query(Reservation).filter(
        Reservation.status.in_([ReservationStatus.active, ReservationStatus.pending]),
        Reservation.ends_at < now,
    ).all()

    for r in expired:
        r.status = ReservationStatus.expired
        _maybe_free_asset(db, r.asset_id)

    # Activate pending reservations whose window has started
    pending = db.query(Reservation).filter(
        Reservation.status == ReservationStatus.pending,
        Reservation.starts_at <= now,
        Reservation.ends_at   >  now,
    ).all()
    for r in pending:
        r.status = ReservationStatus.active
        asset = db.query(Asset).filter(Asset.id == r.asset_id).first()
        if asset and asset.status == AssetStatus.available:
            asset.status = AssetStatus.reserved

    db.commit()
    return len(expired)


def _maybe_free_asset(db: Session, asset_id: int):
    """Set asset back to available if no other active reservation holds it."""
    still_active = db.query(Reservation).filter(
        Reservation.asset_id == asset_id,
        Reservation.status.in_([ReservationStatus.active, ReservationStatus.pending]),
    ).first()
    if not still_active:
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if asset and asset.status == AssetStatus.reserved:
            asset.status = AssetStatus.available


# ── Agent / usage logic ───────────────────────────────────────────────────────

def apply_heartbeat(db: Session, asset: Asset, active_users: int,
                    logged_in_users: list[str], cpu: float, ram: float,
                    disk: float, load: float):
    """
    Update asset status from agent heartbeat.
    Reserved assets stay 'reserved' even when users connect —
    in_use is only set for assets with no reservation (ad-hoc use).
    """
    has_reservation = db.query(Reservation).filter(
        Reservation.asset_id == asset.id,
        Reservation.status.in_([ReservationStatus.active, ReservationStatus.pending]),
    ).first()

    if asset.status not in (AssetStatus.maintenance, AssetStatus.offline):
        if has_reservation:
            asset.status = AssetStatus.reserved  # keep reserved even while in use
        elif active_users > 0:
            asset.status = AssetStatus.in_use
        else:
            asset.status = AssetStatus.available

    metric = HostMetric(
        asset_id=asset.id,
        cpu_percent=cpu,
        ram_percent=ram,
        disk_percent=disk,
        active_users=active_users,
        load_avg=load,
    )
    db.add(metric)

    for username in logged_in_users:
        db.add(ActivityLog(
            asset_id=asset.id,
            username=username,
            event="active_session",
            recorded_at=datetime.utcnow(),
        ))

    db.commit()
    return asset


# ── Ownership check ───────────────────────────────────────────────────────────

def who_has(db: Session, asset_id: int) -> Reservation | None:
    """Return the current active reservation for an asset, if any."""
    now = datetime.utcnow()
    return db.query(Reservation).filter(
        Reservation.asset_id == asset_id,
        Reservation.status.in_([ReservationStatus.active, ReservationStatus.pending]),
        Reservation.starts_at <= now,
        Reservation.ends_at   >  now,
    ).first()


def time_remaining(reservation: Reservation) -> str:
    """Human-readable time remaining on a reservation."""
    delta = reservation.ends_at - datetime.utcnow()
    total = int(delta.total_seconds())
    if total <= 0:
        return "expired"
    h, r = divmod(total, 3600)
    m    = r // 60
    if h:
        return f"{h}h {m}m remaining"
    return f"{m}m remaining"
