CREATE TABLE IF NOT EXISTS controller_mode (
    device_id VARCHAR(100) PRIMARY KEY REFERENCES devices(device_id) ON DELETE CASCADE,
    mode VARCHAR(20) NOT NULL DEFAULT 'NORMAL',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT controller_mode_supported CHECK (mode IN ('NORMAL', 'MANUAL'))
);

INSERT INTO controller_mode (device_id, mode)
SELECT device_id, 'NORMAL'
FROM devices
ON CONFLICT (device_id) DO NOTHING;
