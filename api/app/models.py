from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Device(Base):
    __tablename__ = "devices"

    device_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    firmware_version: Mapped[str] = mapped_column(String(50), nullable=False)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    uptime_seconds: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    wifi_connected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class DeviceConfig(Base):
    __tablename__ = "device_config"

    device_id: Mapped[str] = mapped_column(String(100), ForeignKey("devices.device_id", ondelete="CASCADE"), primary_key=True)
    flow_f1_pulses_per_liter: Mapped[float] = mapped_column(Float, nullable=False, default=420.0)
    flow_f2_pulses_per_liter: Mapped[float] = mapped_column(Float, nullable=False, default=420.0)
    filter_flow_safety_bypass: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    filter_min_flow_lph: Mapped[float] = mapped_column(Float, nullable=False, default=500.0)
    filter_flow_grace_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Telemetry(Base):
    __tablename__ = "telemetry"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(100), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    pool_temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_t1_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_t2_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_t3_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_t4_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_t5_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_t6_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    flow_f1_lph: Mapped[float | None] = mapped_column(Float, nullable=True)
    flow_f2_lph: Mapped[float | None] = mapped_column(Float, nullable=True)


class OutputState(Base):
    __tablename__ = "output_state"

    device_id: Mapped[str] = mapped_column(String(100), ForeignKey("devices.device_id", ondelete="CASCADE"), primary_key=True)
    r1: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    r2: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    r3: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    r4: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    r5: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    r6: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    r7: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    r8: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class OutputCommand(Base):
    __tablename__ = "output_commands"

    device_id: Mapped[str] = mapped_column(String(100), ForeignKey("devices.device_id", ondelete="CASCADE"), primary_key=True)
    output_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pending: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ControllerMode(Base):
    __tablename__ = "controller_mode"

    device_id: Mapped[str] = mapped_column(String(100), ForeignKey("devices.device_id", ondelete="CASCADE"), primary_key=True)
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="NORMAL")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
