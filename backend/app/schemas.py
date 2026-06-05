from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from app.models import UserRole, AssetStatus, ReservationType, ReservationStatus


# --- Auth ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None


# --- Team ---
class TeamCreate(BaseModel):
    name: str
    description: Optional[str] = None

class TeamOut(TeamCreate):
    id: int
    created_at: datetime
    class Config: from_attributes = True


# --- User ---
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    password: str
    role: UserRole = UserRole.user
    team_id: Optional[int] = None

class UserOut(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: UserRole
    team_id: Optional[int]
    is_active: bool
    created_at: datetime
    class Config: from_attributes = True


# --- Asset ---
class AssetCreate(BaseModel):
    hostname: str
    ip_address: Optional[str] = None
    os: Optional[str] = None
    cpu_info: Optional[str] = None
    cpu_cores: Optional[int] = None
    ram_gb: Optional[int] = None
    storage_gb: Optional[int] = None
    location: Optional[str] = None
    environment: Optional[str] = None
    asset_type: Optional[str] = "physical"
    notes: Optional[str] = None
    owner_team_id: Optional[int] = None

class AssetUpdate(AssetCreate):
    hostname: Optional[str] = None
    status: Optional[AssetStatus] = None

class AssetOut(AssetCreate):
    id: int
    status: AssetStatus
    created_at: datetime
    class Config: from_attributes = True


# --- Reservation ---
class ReservationCreate(BaseModel):
    asset_id: int
    reservation_type: ReservationType = ReservationType.hourly
    purpose: Optional[str] = None
    starts_at: datetime
    ends_at: datetime

class ReservationOut(BaseModel):
    id: int
    asset_id: int
    user_id: int
    reservation_type: ReservationType
    status: ReservationStatus
    purpose: Optional[str]
    starts_at: datetime
    ends_at: datetime
    created_at: datetime
    class Config: from_attributes = True


# --- Activity ---
class ActivityLogOut(BaseModel):
    id: int
    asset_id: int
    username: Optional[str]
    event: str
    source_ip: Optional[str]
    recorded_at: datetime
    class Config: from_attributes = True


# --- Metrics ---
class MetricIn(BaseModel):
    hostname: str
    cpu_percent: float
    ram_percent: float
    disk_percent: float
    active_users: int
    load_avg: float
    logged_in_users: List[str] = []

class MetricOut(BaseModel):
    id: int
    asset_id: int
    cpu_percent: float
    ram_percent: float
    disk_percent: float
    active_users: int
    load_avg: float
    recorded_at: datetime
    class Config: from_attributes = True


# --- Reports ---
class UtilizationReport(BaseModel):
    asset_id: int
    hostname: str
    total_reservations: int
    total_hours_reserved: float
    avg_cpu: Optional[float]
    avg_ram: Optional[float]


class NotificationOut(BaseModel):
    id: int
    title: str
    message: str
    channel: str
    is_read: bool
    created_at: datetime
    class Config: from_attributes = True
