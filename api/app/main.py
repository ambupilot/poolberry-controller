import hashlib
import hmac
import os
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import ControllerMode, Device, DeviceConfig, OutputCommand, OutputState, Telemetry
from .schemas import (
    ControllerModeResponse, ControllerModeUpdate,
    DeviceConfigResponse, DeviceConfigUpdate, DeviceStatusResponse,
    HeartbeatRequest, HeartbeatResponse, OperationCommandResponse,
    OutputCommandRequest, OutputCommandResponse, OutputStateRequest, OutputStateResponse,
    TelemetryRequest, TelemetryResponse,
)

app = FastAPI(title="PoolBerry API", version="0.11.0")
DEVICE_ID = os.environ.get("POOLBERRY_DEVICE_ID", "")
DEVICE_TOKEN_SHA256 = os.environ.get("POOLBERRY_DEVICE_TOKEN_SHA256", "").lower()
DEVICE_OFFLINE_AFTER_SECONDS = int(os.environ.get("DEVICE_OFFLINE_AFTER_SECONDS", "30"))
SUPPORTED_OUTPUTS = {f"R{index}" for index in range(1, 9)}
SUPPORTED_COMMANDS = SUPPORTED_OUTPUTS | {"STOP", "FILTERPUMP_ON", "FILTERPUMP_OFF"}


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


def normalize_output_id(output_id: str) -> str:
    normalized = output_id.upper()
    if normalized not in SUPPORTED_OUTPUTS:
        raise HTTPException(status_code=404, detail="Unknown output")
    return normalized


def normalize_command_id(command_id: str) -> str:
    normalized = command_id.upper()
    if normalized not in SUPPORTED_COMMANDS:
        raise HTTPException(status_code=404, detail="Unknown command")
    return normalized


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


def get_or_create_mode(db: Session, device_id: str) -> ControllerMode:
    mode = db.get(ControllerMode, device_id)
    if mode is None:
        mode = ControllerMode(device_id=device_id, mode="NORMAL")
        db.add(mode); db.commit(); db.refresh(mode)
    return mode


def config_response(config: DeviceConfig) -> DeviceConfigResponse:
    return DeviceConfigResponse(
        device_id=config.device_id,
        flow_f1_pulses_per_liter=config.flow_f1_pulses_per_liter,
        flow_f2_pulses_per_liter=config.flow_f2_pulses_per_liter,
        filter_flow_safety_bypass=config.filter_flow_safety_bypass,
        filter_min_flow_lph=config.filter_min_flow_lph,
        filter_flow_grace_seconds=config.filter_flow_grace_seconds,
        updated_at=config.updated_at,
    )


def telemetry_response(t: Telemetry) -> TelemetryResponse:
    return TelemetryResponse(device_id=t.device_id, recorded_at=t.recorded_at, temperature_t1_c=t.temperature_t1_c, temperature_t2_c=t.temperature_t2_c, temperature_t3_c=t.temperature_t3_c, temperature_t4_c=t.temperature_t4_c, temperature_t5_c=t.temperature_t5_c, temperature_t6_c=t.temperature_t6_c, flow_f1_lph=t.flow_f1_lph, flow_f2_lph=t.flow_f2_lph)


def output_state_response(state: OutputState) -> OutputStateResponse:
    return OutputStateResponse(device_id=state.device_id, r1=state.r1, r2=state.r2, r3=state.r3, r4=state.r4, r5=state.r5, r6=state.r6, r7=state.r7, r8=state.r8, updated_at=state.updated_at)


def command_response(command: OutputCommand) -> OutputCommandResponse:
    return OutputCommandResponse(device_id=command.device_id, output_id=command.output_id, enabled=command.enabled, pending=command.pending, updated_at=command.updated_at)


def mode_response(mode: ControllerMode) -> ControllerModeResponse:
    return ControllerModeResponse(device_id=mode.device_id, mode=mode.mode, updated_at=mode.updated_at)


def set_command(db: Session, device_id: str, command_id: str, enabled: bool, now: datetime) -> OutputCommand:
    command = db.get(OutputCommand, (device_id, command_id))
    if command is None:
        command = OutputCommand(device_id=device_id, output_id=command_id, enabled=enabled, pending=True, updated_at=now)
        db.add(command)
    else:
        command.enabled = enabled
        command.pending = True
        command.updated_at = now
    return command


def clear_pending(db: Session, device_id: str, now: datetime) -> None:
    for command in db.scalars(select(OutputCommand).where(OutputCommand.device_id == device_id, OutputCommand.pending.is_(True))).all():
        command.pending = False
        command.updated_at = now


def queue_stop(db: Session, device_id: str, now: datetime) -> OutputCommand:
    clear_pending(db, device_id, now)
    return set_command(db, device_id, "STOP", False, now)


def queue_operation(db: Session, device_id: str, command_id: str, now: datetime) -> OutputCommand:
    clear_pending(db, device_id, now)
    return set_command(db, device_id, command_id, True, now)


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
    config.filter_flow_safety_bypass = payload.filter_flow_safety_bypass
    config.filter_min_flow_lph = payload.filter_min_flow_lph
    config.filter_flow_grace_seconds = payload.filter_flow_grace_seconds
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


@app.get("/internal/v1/devices/{device_id}/mode", response_model=ControllerModeResponse)
def get_controller_mode(device_id: str, db: Session = Depends(get_db)):
    if db.get(Device, device_id) is None: raise HTTPException(status_code=404, detail="Device not found")
    return mode_response(get_or_create_mode(db, device_id))


@app.put("/internal/v1/devices/{device_id}/mode", response_model=ControllerModeResponse)
def update_controller_mode(device_id: str, payload: ControllerModeUpdate, db: Session = Depends(get_db)):
    if db.get(Device, device_id) is None: raise HTTPException(status_code=404, detail="Device not found")
    mode = get_or_create_mode(db, device_id)
    now = datetime.now(timezone.utc)
    target = payload.mode.upper()
    if target == "MANUAL":
        clear_pending(db, device_id, now)
    elif target == "NORMAL":
        queue_stop(db, device_id, now)
    mode.mode = target
    mode.updated_at = now
    db.commit(); db.refresh(mode)
    return mode_response(mode)


@app.post("/internal/v1/devices/{device_id}/stop", response_model=OutputCommandResponse)
def stop_all_outputs(device_id: str, db: Session = Depends(get_db)):
    if db.get(Device, device_id) is None: raise HTTPException(status_code=404, detail="Device not found")
    now = datetime.now(timezone.utc)
    command = queue_stop(db, device_id, now)
    db.commit(); db.refresh(command)
    return command_response(command)


@app.post("/internal/v1/devices/{device_id}/operations/filterpump/on", response_model=OperationCommandResponse)
def filterpump_on(device_id: str, db: Session = Depends(get_db)):
    if db.get(Device, device_id) is None: raise HTTPException(status_code=404, detail="Device not found")
    if get_or_create_mode(db, device_id).mode != "NORMAL":
        raise HTTPException(status_code=409, detail="FILTERPOMP AAN is alleen toegestaan in NORMAL mode")
    state = db.get(OutputState, device_id)
    if state is None: raise HTTPException(status_code=409, detail="Geen actuele outputstatus beschikbaar")
    if state.r4:
        raise HTTPException(status_code=409, detail="FILTERPOMP AAN geblokkeerd: R4 aanvoer VAN zwembad is gesloten")
    if state.r8:
        raise HTTPException(status_code=409, detail="FILTERPOMP AAN geblokkeerd: R8 aanvoer NAAR zwembad is gesloten")
    now = datetime.now(timezone.utc)
    command = queue_operation(db, device_id, "FILTERPUMP_ON", now)
    db.commit(); db.refresh(command)
    return OperationCommandResponse(device_id=device_id, command="FILTERPUMP_ON", pending=True, detail="Normale zwembadroute geldig; filterpomp-startopdracht aangeboden", updated_at=command.updated_at)


@app.post("/internal/v1/devices/{device_id}/operations/filterpump/off", response_model=OperationCommandResponse)
def filterpump_off(device_id: str, db: Session = Depends(get_db)):
    if db.get(Device, device_id) is None: raise HTTPException(status_code=404, detail="Device not found")
    if get_or_create_mode(db, device_id).mode != "NORMAL":
        raise HTTPException(status_code=409, detail="FILTERPOMP UIT is alleen toegestaan in NORMAL mode; gebruik STOP in MANUAL")
    now = datetime.now(timezone.utc)
    command = queue_operation(db, device_id, "FILTERPUMP_OFF", now)
    db.commit(); db.refresh(command)
    return OperationCommandResponse(device_id=device_id, command="FILTERPUMP_OFF", pending=True, detail="Installatie wordt lokaal door de controller naar fail-safe teruggebracht", updated_at=command.updated_at)


@app.put("/internal/v1/devices/{device_id}/outputs/{output_id}/command", response_model=OutputCommandResponse)
def set_output_command(device_id: str, output_id: str, payload: OutputCommandRequest, db: Session = Depends(get_db)):
    if db.get(Device, device_id) is None: raise HTTPException(status_code=404, detail="Device not found")
    if get_or_create_mode(db, device_id).mode != "MANUAL":
        raise HTTPException(status_code=409, detail="Direct output commands require MANUAL mode")
    output_id = normalize_output_id(output_id)
    now = datetime.now(timezone.utc)
    command = set_command(db, device_id, output_id, payload.enabled, now)
    db.commit(); db.refresh(command)
    return command_response(command)


@app.get("/api/v1/devices/{device_id}/commands/next", response_model=OutputCommandResponse | None)
def get_next_command(device_id: str, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    authorize_device(device_id, authorization)
    command = db.scalar(select(OutputCommand).where(OutputCommand.device_id == device_id, OutputCommand.pending.is_(True)).order_by(OutputCommand.updated_at.asc()).limit(1))
    return None if command is None else command_response(command)


@app.post("/api/v1/devices/{device_id}/commands/{command_id}/ack", response_model=OutputCommandResponse)
def acknowledge_command(device_id: str, command_id: str, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    authorize_device(device_id, authorization)
    command_id = normalize_command_id(command_id)
    command = db.get(OutputCommand, (device_id, command_id))
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
