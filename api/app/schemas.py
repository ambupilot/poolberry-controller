from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HeartbeatRequest(BaseModel):
    firmware_version: str = Field(min_length=1, max_length=50)
    uptime: int = Field(ge=0)
    wifi_connected: bool


class HeartbeatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
