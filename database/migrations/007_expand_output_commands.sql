ALTER TABLE output_commands
    DROP CONSTRAINT IF EXISTS output_commands_supported_output;

ALTER TABLE output_commands
    ADD CONSTRAINT output_commands_supported_output
    CHECK (output_id IN ('R1','R2','R3','R4','R5','R6','R7','R8'));
