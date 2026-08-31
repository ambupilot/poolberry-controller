CREATE TABLE IF NOT EXISTS output_commands (
    device_id VARCHAR(100) NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    output_id VARCHAR(10) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    pending BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (device_id, output_id),
    CONSTRAINT output_commands_supported_output CHECK (output_id = 'R1')
);
