from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Device(Base):
    __tablename__ = "devices"

    device_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    firmware_version: Mapped[str] = mapped_column(String(50), nullable=False)
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    uptime_seconds: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    wifi_connected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Telemetry(Base):
    __tablename__ = "telemetry"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Legacy field retained while the prototype database is migrated.
    pool_temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)

    temperature_t1_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_t2_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_t3_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_t4_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_t5_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_t6_c: Mapped[float | None] = mapped_column(Float, nullable=True)
