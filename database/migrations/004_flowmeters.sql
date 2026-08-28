ALTER TABLE telemetry
    ADD COLUMN IF NOT EXISTS flow_f1_lph DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS flow_f2_lph DOUBLE PRECISION;

CREATE TABLE IF NOT EXISTS device_config (
    device_id VARCHAR(100) PRIMARY KEY REFERENCES devices(device_id) ON DELETE CASCADE,
    flow_f1_pulses_per_liter DOUBLE PRECISION NOT NULL DEFAULT 420,
    flow_f2_pulses_per_liter DOUBLE PRECISION NOT NULL DEFAULT 420,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO device_config (device_id)
SELECT device_id FROM devices
ON CONFLICT (device_id) DO NOTHING;
