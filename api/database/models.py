"""
SQLAlchemy ORM models for SignalLens AI.
Supports both PostgreSQL (Supabase) and SQLite with async engine.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    role = Column(String(50), default="user", nullable=False)
    tier = Column(String(50), default="base", nullable=False)  # base, cyber_pro, sovereign
    refresh_token_hash = Column(String(255), nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    lockout_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    files = relationship("FileModel", back_populates="user", cascade="all, delete-orphan")
    analyses = relationship("AnalysisModel", back_populates="user", cascade="all, delete-orphan")
    subscription = relationship("SubscriptionModel", back_populates="user", uselist=False)
    payments = relationship("PaymentModel", back_populates="user", cascade="all, delete-orphan")


class FileModel(Base):
    __tablename__ = "files"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=True)
    file_name = Column(String(255), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    storage_path = Column(String(512), nullable=False)
    format = Column(String(50), nullable=False)
    duration_seconds = Column(Float, default=0.0)
    sample_rate = Column(Integer, default=44100)
    is_deleted = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("UserModel", back_populates="files")
    analyses = relationship("AnalysisModel", back_populates="file")


class AnalysisModel(Base):
    __tablename__ = "analyses"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=True)
    file_id = Column(String(36), ForeignKey("files.id"), index=True, nullable=True)
    file_name = Column(String(255), nullable=False)
    predicted_class = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=False)
    is_anomaly = Column(Boolean, default=False)
    anomaly_score = Column(Float, default=0.0)
    report_text = Column(Text, nullable=True)
    metrics_json = Column(JSON, nullable=True)
    advanced_json = Column(JSON, nullable=True)
    is_deleted = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("UserModel", back_populates="analyses")
    file = relationship("FileModel", back_populates="analyses")


class SubscriptionModel(Base):
    __tablename__ = "subscriptions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), unique=True, index=True, nullable=False)
    tier = Column(String(50), default="base", nullable=False)
    billing_cycle = Column(String(50), default="monthly", nullable=False)
    status = Column(String(50), default="active", nullable=False)  # active, past_due, canceled
    current_period_end = Column(DateTime(timezone=True), nullable=False)
    payment_provider = Column(String(50), default="stripe", nullable=False)
    provider_subscription_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("UserModel", back_populates="subscription")


class BillingEventModel(Base):
    __tablename__ = "billing_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    event_type = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False)
    raw_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class UsageMeterModel(Base):
    __tablename__ = "usage_meters"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=False)
    period_start = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    uploads_count = Column(Integer, default=0, nullable=False)
    storage_bytes_used = Column(Integer, default=0, nullable=False)
    sovereign_compute_seconds_used = Column(Float, default=0.0, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class PaymentModel(Base):
    __tablename__ = "payments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), index=True, nullable=True)
    order_id = Column(String(100), unique=True, index=True, nullable=False)
    plan = Column(String(50), nullable=False)  # cyber_pro, sovereign
    currency = Column(String(10), default="INR", nullable=False)  # INR, USD
    billing_cycle = Column(String(50), default="monthly", nullable=False)  # monthly, annual
    base_amount = Column(Float, nullable=False)
    tax_amount = Column(Float, nullable=False)  # 18% GST for INR
    total_amount = Column(Float, nullable=False)
    payment_method = Column(String(50), default="upi", nullable=False)  # upi, card, netbanking, simulation
    gateway = Column(String(50), default="mock", nullable=False)  # mock, razorpay
    status = Column(String(50), default="pending", nullable=False)  # pending, completed, failed
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    raw_metadata = Column(JSON, nullable=True)

    user = relationship("UserModel", back_populates="payments")
