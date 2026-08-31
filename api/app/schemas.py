from datetime import datetime

from pydantic import BaseModel, Field


class HeartbeatRequest(BaseModel):
    firmware_version: str = Field(min_length=1, max_length=50)
    uptime: int = Field(ge=0)
    wifi_connected: bool


class HeartbeatResponse(BaseModel):
    device_id: str
    firmware_version: str
    last_seen: datetime
    uptime_seconds: int
    wifi_connected: bool
    status: str = "online"


class DeviceStatusResponse(BaseModel):
    device_id: str
    firmware_version: str
    first_seen: datetime
    last_seen: datetime
    uptime_seconds: int
    wifi_connected: bool
    status: str


class DeviceConfigResponse(BaseModel):
    device_id: str
    flow_f1_pulses_per_liter: float
    flow_f2_pulses_per_liter: float
    filter_flow_safety_bypass: bool
    filter_min_flow_lph: float
    filter_flow_grace_seconds: int
    updated_at: datetime


class DeviceConfigUpdate(BaseModel):
    flow_f1_pulses_per_liter: float = Field(gt=0, le=100000)
    flow_f2_pulses_per_liter: float = Field(gt=0, le=100000)
    filter_flow_safety_bypass: bool = True
    filter_min_flow_lph: float = Field(default=500.0, ge=0, le=100000)
    filter_flow_grace_seconds: int = Field(default=10, ge=1, le=120)


class TelemetryRequest(BaseModel):
    temperature_t1_c: float | None = Field(default=None, ge=-55, le=125)
    temperature_t2_c: float | None = Field(default=None, ge=-55, le=125)
    temperature_t3_c: float | None = Field(default=None, ge=-55, le=125)
    temperature_t4_c: float | None = Field(default=None, ge=-55, le=125)
    temperature_t5_c: float | None = Field(default=None, ge=-55, le=125)
    temperature_t6_c: float | None = Field(default=None, ge=-55, le=125)
    flow_f1_lph: float | None = Field(default=None, ge=0)
    flow_f2_lph: float | None = Field(default=None, ge=0)


class TelemetryResponse(BaseModel):
    device_id: str
    recorded_at: datetime
    temperature_t1_c: float | None = None
    temperature_t2_c: float | None = None
    temperature_t3_c: float | None = None
    temperature_t4_c: float | None = None
    temperature_t5_c: float | None = None
    temperature_t6_c: float | None = None
    flow_f1_lph: float | None = None
    flow_f2_lph: float | None = None


class OutputStateRequest(BaseModel):
    r1: bool
    r2: bool
    r3: bool
    r4: bool
    r5: bool
    r6: bool
    r7: bool
    r8: bool


class OutputStateResponse(OutputStateRequest):
    device_id: str
    updated_at: datetime


class OutputCommandRequest(BaseModel):
    enabled: bool


class OutputCommandResponse(BaseModel):
    device_id: str
    output_id: str
    enabled: bool
    pending: bool
    updated_at: datetime


class ControllerModeUpdate(BaseModel):
    mode: str = Field(pattern="^(NORMAL|MANUAL)$")


class ControllerModeResponse(BaseModel):
    device_id: str
    mode: str
    updated_at: datetime


class OperationCommandResponse(BaseModel):
    device_id: str
    command: str
    pending: bool
    detail: str
    updated_at: datetime
