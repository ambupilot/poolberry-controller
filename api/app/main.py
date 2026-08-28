import hashlib
import hmac
import os
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import Device, Telemetry
from .schemas import (
    DeviceStatusResponse,
    HeartbeatRequest,
    HeartbeatResponse,
    TelemetryRequest,
    TelemetryResponse,
)

app = FastAPI(title="PoolBerry API", version="0.4.0")

DEVICE_ID = os.environ.get("POOLBERRY_DEVICE_ID", "")
DEVICE_TOKEN_SHA256 = os.environ.get("POOLBERRY_DEVICE_TOKEN_SHA256", "").lower()
DEVICE_OFFLINE_AFTER_SECONDS = int(os.environ.get("DEVICE_OFFLINE_AFTER_SECONDS", "30"))


def authorize_device(device_id: str, authorization: str | None) -> None:
    if not DEVICE_ID or not DEVICE_TOKEN_SHA256:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Device authentication is not configured",
        )

    if device_id != DEVICE_ID:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized device")

    scheme, separator, token = (authorization or "").partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    supplied_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(supplied_hash, DEVICE_TOKEN_SHA256):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device token")


def device_status(device: Device) -> str:
    now = datetime.now(timezone.utc)
    last_seen = device.last_seen
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)

    age_seconds = (now - last_seen).total_seconds()
    return "online" if age_seconds <= DEVICE_OFFLINE_AFTER_SECONDS else "offline"


def telemetry_response(telemetry: Telemetry) -> TelemetryResponse:
    return TelemetryResponse(
        device_id=telemetry.device_id,
        recorded_at=telemetry.recorded_at,
        temperature_t1_c=telemetry.temperature_t1_c,
        temperature_t2_c=telemetry.temperature_t2_c,
        temperature_t3_c=telemetry.temperature_t3_c,
        temperature_t4_c=telemetry.temperature_t4_c,
        temperature_t5_c=telemetry.temperature_t5_c,
        temperature_t6_c=telemetry.temperature_t6_c,
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get(
    "/internal/v1/devices/{device_id}",
    response_model=DeviceStatusResponse,
)
def get_device_status(device_id: str, db: Session = Depends(get_db)):
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    return DeviceStatusResponse(
        device_id=device.device_id,
        firmware_version=device.firmware_version,
        first_seen=device.first_seen,
        last_seen=device.last_seen,
        uptime_seconds=device.uptime_seconds,
        wifi_connected=device.wifi_connected,
        status=device_status(device),
    )


@app.get(
    "/internal/v1/devices/{device_id}/telemetry/latest",
    response_model=TelemetryResponse,
)
def get_latest_telemetry(device_id: str, db: Session = Depends(get_db)):
    telemetry = db.scalar(
        select(Telemetry)
        .where(Telemetry.device_id == device_id)
        .order_by(Telemetry.recorded_at.desc())
        .limit(1)
    )
    if telemetry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Telemetry not found")

    return telemetry_response(telemetry)


@app.post(
    "/api/v1/devices/{device_id}/heartbeat",
    response_model=HeartbeatResponse,
)
def heartbeat(
    device_id: str,
    payload: HeartbeatRequest,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    authorize_device(device_id, authorization)

    now = datetime.now(timezone.utc)
    device = db.get(Device, device_id)

    if device is None:
        device = Device(
            device_id=device_id,
            firmware_version=payload.firmware_version,
            last_seen=now,
            uptime_seconds=payload.uptime,
            wifi_connected=payload.wifi_connected,
        )
        db.add(device)
    else:
        device.firmware_version = payload.firmware_version
        device.last_seen = now
        device.uptime_seconds = payload.uptime
        device.wifi_connected = payload.wifi_connected

    db.commit()
    db.refresh(device)

    return HeartbeatResponse(
        device_id=device.device_id,
        firmware_version=device.firmware_version,
        last_seen=device.last_seen,
        uptime_seconds=device.uptime_seconds,
        wifi_connected=device.wifi_connected,
        status="online",
    )


@app.post(
    "/api/v1/devices/{device_id}/telemetry",
    response_model=TelemetryResponse,
)
def post_telemetry(
    device_id: str,
    payload: TelemetryRequest,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    authorize_device(device_id, authorization)

    if db.get(Device, device_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")

    values = payload.model_dump()
    if not any(value is not None for value in values.values()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Telemetry contains no temperature values",
        )

    telemetry = Telemetry(
        device_id=device_id,
        **values,
    )
    db.add(telemetry)
    db.commit()
    db.refresh(telemetry)

    return telemetry_response(telemetry)
