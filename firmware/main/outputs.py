from machine import Pin

# PoolBerry main-controller output bank.
# Logical ON is currently mapped to GPIO HIGH, matching the tested LED/input
# behavior of the relay modules. Confirm the physical COM/NO relay contact
# behavior before connecting pumps or actuators.
OUTPUT_ON_LEVEL = 1
OUTPUT_OFF_LEVEL = 0

OUTPUTS = {
    "R1": {"gpio": 8, "role": "FILTERPOMP", "kind": "pump"},
    "R2": {"gpio": 9, "role": "WARMTEPOMP", "kind": "pump"},
    "R3": {"gpio": 10, "role": "BRONPOMP", "kind": "pump"},
    "R4": {"gpio": 11, "role": "AANVOER_VAN_ZWEMBAD", "kind": "valve", "valve_type": "NO"},
    "R5": {"gpio": 12, "role": "BRONPOMP_AANVOER", "kind": "valve", "valve_type": "NC"},
    "R6": {"gpio": 13, "role": "TUIN", "kind": "valve", "valve_type": "NO"},
    "R7": {"gpio": 14, "role": "BYPASS_COLLECTOR", "kind": "valve", "valve_type": "NC"},
    "R8": {"gpio": 15, "role": "AANVOER_NAAR_ZWEMBAD", "kind": "valve", "valve_type": "NO"},
}


def initialise_outputs():
    """Initialise every output immediately in the logical OFF state."""
    pins = {}
    for output_id, definition in OUTPUTS.items():
        pins[output_id] = Pin(definition["gpio"], Pin.OUT, value=OUTPUT_OFF_LEVEL)
    return pins


def output_states(pins):
    """Return logical commanded states, independent of raw GPIO representation."""
    return {
        output_id.lower(): pins[output_id].value() == OUTPUT_ON_LEVEL
        for output_id in OUTPUTS
    }
