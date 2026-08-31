ALTER TABLE device_config
    ADD COLUMN IF NOT EXISTS filter_flow_safety_bypass BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS filter_min_flow_lph DOUBLE PRECISION NOT NULL DEFAULT 500.0,
    ADD COLUMN IF NOT EXISTS filter_flow_grace_seconds INTEGER NOT NULL DEFAULT 10;

ALTER TABLE output_commands
    DROP CONSTRAINT IF EXISTS output_commands_supported_output;

ALTER TABLE output_commands
    ADD CONSTRAINT output_commands_supported_output
    CHECK (output_id IN (
        'R1','R2','R3','R4','R5','R6','R7','R8',
        'STOP','FILTERPUMP_ON','FILTERPUMP_OFF'
    ));
