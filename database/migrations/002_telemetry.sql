CREATE TABLE IF NOT EXISTS telemetry (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(100) NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    pool_temperature_c DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_telemetry_device_recorded_at
    ON telemetry (device_id, recorded_at DESC);
