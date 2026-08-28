ALTER TABLE telemetry
    ALTER COLUMN pool_temperature_c DROP NOT NULL,
    ADD COLUMN IF NOT EXISTS temperature_t1_c DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS temperature_t2_c DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS temperature_t3_c DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS temperature_t4_c DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS temperature_t5_c DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS temperature_t6_c DOUBLE PRECISION;

COMMENT ON COLUMN telemetry.temperature_t1_c IS 'T1 - BUITEN';
COMMENT ON COLUMN telemetry.temperature_t2_c IS 'T2 - ZWEMBAD';
COMMENT ON COLUMN telemetry.temperature_t3_c IS 'T3 - WARMTEPOMP';
COMMENT ON COLUMN telemetry.temperature_t4_c IS 'T4 - COLLECTOR';
COMMENT ON COLUMN telemetry.temperature_t5_c IS 'T5 - ZWEMBAD IN';
COMMENT ON COLUMN telemetry.temperature_t6_c IS 'T6 - BINNEN';
