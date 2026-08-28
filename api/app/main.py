import hashlib
import hmac
import os
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Header, HTTPException, status
from sqlalchemy.orm import Session

from .database import get_db
from .models import Device
from .schemas import HeartbeatRequest, HeartbeatResponse

app = FastAPI(title="PoolBerry API", version="0.1.0")

DEVICE_ID = os.environ.get("POOLBERRY_DEVICE_ID", "")
DEVICE_TOKEN_SHA256 = os.environ.get("POOLBERRY_DEVICE_TOKEN_SHA256", "").lower()


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


@app.get("/health")
def health():
    return {"status": "ok"}


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
