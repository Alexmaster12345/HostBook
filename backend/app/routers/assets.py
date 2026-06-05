from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models import Asset, AssetStatus, User
from app.schemas import AssetCreate, AssetOut, AssetUpdate
from app.auth import get_current_user, require_admin

router = APIRouter(prefix="/api/v1/assets", tags=["assets"])


@router.get("/", response_model=List[AssetOut])
def list_assets(
    status: Optional[AssetStatus] = None,
    environment: Optional[str] = None,
    asset_type: Optional[str] = None,
    os: Optional[str] = None,
    location: Optional[str] = None,
    team_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Asset)
    if status:       q = q.filter(Asset.status == status)
    if environment:  q = q.filter(Asset.environment == environment)
    if asset_type:   q = q.filter(Asset.asset_type == asset_type)
    if os:           q = q.filter(Asset.os.ilike(f"%{os}%"))
    if location:     q = q.filter(Asset.location.ilike(f"%{location}%"))
    if team_id:      q = q.filter(Asset.owner_team_id == team_id)
    return q.all()


@router.get("/{asset_id}", response_model=AssetOut)
def get_asset(asset_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(404, "Asset not found")
    return asset


@router.post("/", response_model=AssetOut, status_code=201)
def create_asset(payload: AssetCreate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    if db.query(Asset).filter(Asset.hostname == payload.hostname).first():
        raise HTTPException(400, "Hostname already registered")
    asset = Asset(**payload.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.patch("/{asset_id}", response_model=AssetOut)
def update_asset(asset_id: int, payload: AssetUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(404, "Asset not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(asset, field, value)
    db.commit()
    db.refresh(asset)
    return asset


@router.delete("/{asset_id}", status_code=204)
def delete_asset(asset_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(404, "Asset not found")
    db.delete(asset)
    db.commit()
