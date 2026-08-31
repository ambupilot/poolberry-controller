import hashlib
import hmac
import os
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import Device, DeviceConfig, OutputCommand, OutputState, Telemetry
from .schemas import (
    DeviceConfigResponse, DeviceConfigUpdate, DeviceStatusResponse,
    HeartbeatRequest, HeartbeatResponse, OutputCommandRequest,
    OutputCommandResponse, OutputStateRequest, OutputStateResponse,
    TelemetryRequest, TelemetryResponse,
)

app = FastAPI(title="PoolBerry API", version="0.7.0")
DEVICE_ID = os.environ.get("POOLBERRY_DEVICE_ID", "")
DEVICE_TOKEN_SHA256 = os.environ.get("POOLBERRY_DEVICE_TOKEN_SHA256", "").lower()
DEVICE_OFFLINE_AFTER_SECONDS = int(os.environ.get("DEVICE_OFFLINE_AFTER_SECONDS", "30"))


def authorize_device(device_id: str, authorization: str | None) -> None:
    if not DEVICE_ID or not DEVICE_TOKEN_SHA256:
        raise HTTPException(status_code=503, detail="Device authentication is not configured")
    if device_id != DEVICE_ID:
        raise HTTPException(status_code=401, detail="Unauthorized device")
    scheme, separator, token = (authorization or "").partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    supplied_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(supplied_hash, DEVICE_TOKEN_SHA256):
        raise HTTPException(status_code=401, detail="Invalid device token")


def device_status(device: Device) -> str:
    now = datetime.now(timezone.utc)
    last_seen = device.last_seen
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    return "online" if (now - last_seen).total_seconds() <= DEVICE_OFFLINE_AFTER_SECONDS else "offline"


def get_or_create_config(db: Session, device_id: str) -> DeviceConfig:
    config = db.get(DeviceConfig, device_id)
    if config is None:
        config = DeviceConfig(device_id=device_id)
        db.add(config); db.commit(); db.refresh(config)
    return config


def config_response(config: DeviceConfig) -> DeviceConfigResponse:
    return DeviceConfigResponse(device_id=config.device_id, flow_f1_pulses_per_liter=config.flow_f1_pulses_per_liter, flow_f2_pulses_per_liter=config.flow_f2_pulses_per_liter, updated_at=config.updated_at)


def telemetry_response(t: Telemetry) -> TelemetryResponse:
    return TelemetryResponse(device_id=t.device_id, recorded_at=t.recorded_at, temperature_t1_c=t.temperature_t1_c, temperature_t2_c=t.temperature_t2_c, temperature_t3_c=t.temperature_t3_c, temperature_t4_c=t.temperature_t4_c, temperature_t5_c=t.temperature_t5_c, temperature_t6_c=t.temperature_t6_c, flow_f1_lph=t.flow_f1_lph, flow_f2_lph=t.flow_f2_lph)


def output_state_response(state: OutputState) -> OutputStateResponse:
    return OutputStateResponse(device_id=state.device_id, r1=state.r1, r2=state.r2, r3=state.r3, r4=state.r4, r5=state.r5, r6=state.r6, r7=state.r7, r8=state.r8, updated_at=state.updated_at)


def command_response(command: OutputCommand) -> OutputCommandResponse:
    return OutputCommandResponse(device_id=command.device_id, output_id=command.output_id, enabled=command.enabled, pending=command.pending, updated_at=command.updated_at)


@app.get("/health")
def health(): return {"status": "ok"}


@app.get("/internal/v1/devices/{device_id}", response_model=DeviceStatusResponse)
def get_device_status(device_id: str, db: Session = Depends(get_db)):
    device = db.get(Device, device_id)
    if device is None: raise HTTPException(status_code=404, detail="Device not found")
    return DeviceStatusResponse(device_id=device.device_id, firmware_version=device.firmware_version, first_seen=device.first_seen, last_seen=device.last_seen, uptime_seconds=device.uptime_seconds, wifi_connected=device.wifi_connected, status=device_status(device))


@app.get("/internal/v1/devices/{device_id}/config", response_model=DeviceConfigResponse)
def get_internal_config(device_id: str, db: Session = Depends(get_db)):
    if db.get(Device, device_id) is None: raise HTTPException(status_code=404, detail="Device not found")
    return config_response(get_or_create_config(db, device_id))


@app.put("/internal/v1/devices/{device_id}/config", response_model=DeviceConfigResponse)
def update_internal_config(device_id: str, payload: DeviceConfigUpdate, db: Session = Depends(get_db)):
    if db.get(Device, device_id) is None: raise HTTPException(status_code=404, detail="Device not found")
    config = get_or_create_config(db, device_id)
    config.flow_f1_pulses_per_liter = payload.flow_f1_pulses_per_liter
    config.flow_f2_pulses_per_liter = payload.flow_f2_pulses_per_liter
    config.updated_at = datetime.now(timezone.utc)
    db.commit(); db.refresh(config)
    return config_response(config)


@app.get("/api/v1/devices/{device_id}/config", response_model=DeviceConfigResponse)
def get_device_config(device_id: str, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    authorize_device(device_id, authorization)
    if db.get(Device, device_id) is None: raise HTTPException(status_code=404, detail="Device not found")
    return config_response(get_or_create_config(db, device_id))


@app.get("/internal/v1/devices/{device_id}/telemetry/latest", response_model=TelemetryResponse)
def get_latest_telemetry(device_id: str, db: Session = Depends(get_db)):
    telemetry = db.scalar(select(Telemetry).where(Telemetry.device_id == device_id).order_by(Telemetry.recorded_at.desc()).limit(1))
    if telemetry is None: raise HTTPException(status_code=404, detail="Telemetry not found")
    return telemetry_response(telemetry)


@app.get("/internal/v1/devices/{device_id}/output-state", response_model=OutputStateResponse)
def get_output_state(device_id: str, db: Session = Depends(get_db)):
    state = db.get(OutputState, device_id)
    if state is None: raise HTTPException(status_code=404, detail="Output state not found")
    return output_state_response(state)


@app.put("/internal/v1/devices/{device_id}/outputs/R1/command", response_model=OutputCommandResponse)
def set_r1_command(device_id: str, payload: OutputCommandRequest, db: Session = Depends(get_db)):
    if db.get(Device, device_id) is None: raise HTTPException(status_code=404, detail="Device not found")
    now = datetime.now(timezone.utc)
    command = db.get(OutputCommand, (device_id, "R1"))
    if command is None:
        command = OutputCommand(device_id=device_id, output_id="R1", enabled=payload.enabled, pending=True, updated_at=now)
        db.add(command)
    else:
        command.enabled = payload.enabled; command.pending = True; command.updated_at = now
    db.commit(); db.refresh(command)
    return command_response(command)


@app.get("/api/v1/devices/{device_id}/commands/next", response_model=OutputCommandResponse | None)
def get_next_command(device_id: str, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    authorize_device(device_id, authorization)
    command = db.scalar(select(OutputCommand).where(OutputCommand.device_id == device_id, OutputCommand.pending.is_(True)).order_by(OutputCommand.updated_at.asc()).limit(1))
    return None if command is None else command_response(command)


@app.post("/api/v1/devices/{device_id}/commands/{output_id}/ack", response_model=OutputCommandResponse)
def acknowledge_command(device_id: str, output_id: str, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    authorize_device(device_id, authorization)
    command = db.get(OutputCommand, (device_id, output_id.upper()))
    if command is None: raise HTTPException(status_code=404, detail="Command not found")
    command.pending = False; command.updated_at = datetime.now(timezone.utc)
    db.commit(); db.refresh(command)
    return command_response(command)


@app.post("/api/v1/devices/{device_id}/heartbeat", response_model=HeartbeatResponse)
def heartbeat(device_id: str, payload: HeartbeatRequest, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    authorize_device(device_id, authorization); now = datetime.now(timezone.utc); device = db.get(Device, device_id)
    if device is None:
        device = Device(device_id=device_id, firmware_version=payload.firmware_version, last_seen=now, uptime_seconds=payload.uptime, wifi_connected=payload.wifi_connected); db.add(device)
    else:
        device.firmware_version = payload.firmware_version; device.last_seen = now; device.uptime_seconds = payload.uptime; device.wifi_connected = payload.wifi_connected
    db.commit(); db.refresh(device)
    return HeartbeatResponse(device_id=device.device_id, firmware_version=device.firmware_version, last_seen=device.last_seen, uptime_seconds=device.uptime_seconds, wifi_connected=device.wifi_connected, status="online")


@app.post("/api/v1/devices/{device_id}/telemetry", response_model=TelemetryResponse)
def post_telemetry(device_id: str, payload: TelemetryRequest, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    authorize_device(device_id, authorization)
    if db.get(Device, device_id) is None: raise HTTPException(status_code=404, detail="Device not found")
    values = payload.model_dump()
    if not any(value is not None for value in values.values()): raise HTTPException(status_code=422, detail="Telemetry contains no values")
    telemetry = Telemetry(device_id=device_id, **values); db.add(telemetry); db.commit(); db.refresh(telemetry)
    return telemetry_response(telemetry)


@app.post("/api/v1/devices/{device_id}/output-state", response_model=OutputStateResponse)
def post_output_state(device_id: str, payload: OutputStateRequest, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    authorize_device(device_id, authorization)
    if db.get(Device, device_id) is None: raise HTTPException(status_code=404, detail="Device not found")
    now = datetime.now(timezone.utc); state = db.get(OutputState, device_id); values = payload.model_dump()
    if state is None:
        state = OutputState(device_id=device_id, updated_at=now, **values); db.add(state)
    else:
        for name, value in values.items(): setattr(state, name, value)
        state.updated_at = now
    db.commit(); db.refresh(state)
    return output_state_response(state)
