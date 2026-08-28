import hashlib
import hmac
import os
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Header, HTTPException, status
from sqlalchemy.orm import Session

from .database import get_db
from .models import Device
from .schemas import DeviceStatusResponse, HeartbeatRequest, HeartbeatResponse

app = FastAPI(title="PoolBerry API", version="0.2.0")

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
