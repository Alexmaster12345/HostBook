from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey,
    Text, Enum, Float
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import enum

Base = declarative_base()


class UserRole(str, enum.Enum):
    admin = "admin"
    infra_engineer = "infra_engineer"
    team_lead = "team_lead"
    user = "user"


class AssetStatus(str, enum.Enum):
    available = "available"
    reserved = "reserved"
    in_use = "in_use"
    maintenance = "maintenance"
    offline = "offline"


class ReservationType(str, enum.Enum):
    hourly = "hourly"
    daily = "daily"
    multi_day = "multi_day"
    recurring = "recurring"


class ReservationStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    expired = "expired"
    cancelled = "cancelled"


class Team(Base):
    __tablename__ = "teams"
    id          = Column(Integer, primary_key=True)
    name        = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    created_at  = Column(DateTime, default=datetime.utcnow)
    users       = relationship("User", back_populates="team")
    assets      = relationship("Asset", back_populates="owner_team")


class User(Base):
    __tablename__ = "users"
    id            = Column(Integer, primary_key=True)
    username      = Column(String(80), unique=True, nullable=False)
    email         = Column(String(120), unique=True, nullable=False)
    full_name     = Column(String(150))
    hashed_password = Column(String(255), nullable=False)
    role          = Column(Enum(UserRole), default=UserRole.user)
    team_id       = Column(Integer, ForeignKey("teams.id"), nullable=True)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    team          = relationship("Team", back_populates="users")
    reservations  = relationship("Reservation", back_populates="user")


class Asset(Base):
    __tablename__ = "assets"
    id            = Column(Integer, primary_key=True)
    hostname      = Column(String(255), unique=True, nullable=False)
    ip_address    = Column(String(45))
    os            = Column(String(100))
    cpu_info      = Column(String(255))
    cpu_cores     = Column(Integer)
    ram_gb        = Column(Integer)
    storage_gb    = Column(Integer)
    location      = Column(String(255))
    environment   = Column(String(100))  # dev, qa, staging, prod, lab
    asset_type    = Column(String(100))  # physical, vm, workstation, lab
    status        = Column(Enum(AssetStatus), default=AssetStatus.available)
    owner_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    notes         = Column(Text)
    created_at    = Column(DateTime, default=datetime.utcnow)
    owner_team    = relationship("Team", back_populates="assets")
    reservations  = relationship("Reservation", back_populates="asset")
    activity_logs = relationship("ActivityLog", back_populates="asset")
    metrics       = relationship("HostMetric", back_populates="asset")


class Reservation(Base):
    __tablename__ = "reservations"
    id            = Column(Integer, primary_key=True)
    asset_id      = Column(Integer, ForeignKey("assets.id"), nullable=False)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=False)
    reservation_type = Column(Enum(ReservationType), default=ReservationType.hourly)
    status        = Column(Enum(ReservationStatus), default=ReservationStatus.pending)
    purpose       = Column(Text)
    starts_at     = Column(DateTime, nullable=False)
    ends_at       = Column(DateTime, nullable=False)
    created_at    = Column(DateTime, default=datetime.utcnow)
    asset         = relationship("Asset", back_populates="reservations")
    user          = relationship("User", back_populates="reservations")


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id         = Column(Integer, primary_key=True)
    asset_id   = Column(Integer, ForeignKey("assets.id"), nullable=False)
    username   = Column(String(80))
    event      = Column(String(100))   # login, logout, ssh_connect, ssh_disconnect
    source_ip  = Column(String(45))
    session_id = Column(String(255))
    recorded_at = Column(DateTime, default=datetime.utcnow)
    asset      = relationship("Asset", back_populates="activity_logs")


class HostMetric(Base):
    __tablename__ = "host_metrics"
    id           = Column(Integer, primary_key=True)
    asset_id     = Column(Integer, ForeignKey("assets.id"), nullable=False)
    cpu_percent  = Column(Float)
    ram_percent  = Column(Float)
    disk_percent = Column(Float)
    active_users = Column(Integer, default=0)
    load_avg     = Column(Float)
    recorded_at  = Column(DateTime, default=datetime.utcnow)
    asset        = relationship("Asset", back_populates="metrics")


class Notification(Base):
    __tablename__ = "notifications"
    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    title      = Column(String(255))
    message    = Column(Text)
    channel    = Column(String(50))  # email, slack, teams
    is_read    = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
