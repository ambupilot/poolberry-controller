from machine import Pin

# PoolBerry main-controller output bank.
# Physical relay behavior has been verified on the installed relay modules:
# GPIO LOW  -> relay energised   -> COM/NO closed  -> logical relay ON
# GPIO HIGH -> relay de-energised -> COM/NO open   -> logical relay OFF
#
# The relay inputs are therefore ACTIVE-LOW.
# Logical semantics throughout the application remain:
#   True  = relay ON / energised
#   False = relay OFF / de-energised
OUTPUT_ON_LEVEL = 0
OUTPUT_OFF_LEVEL = 1

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


def set_output(pins, output_id, enabled):
    """Set one known output using logical True=ON / False=OFF semantics."""
    if output_id not in OUTPUTS:
        raise ValueError("Unknown output: " + str(output_id))
    pins[output_id].value(OUTPUT_ON_LEVEL if enabled else OUTPUT_OFF_LEVEL)


def all_outputs_off(pins):
    """Immediately force all relay outputs to the logical OFF level."""
    for output_id in OUTPUTS:
        pins[output_id].value(OUTPUT_OFF_LEVEL)


def output_states(pins):
    """Return logical states, independent of raw GPIO representation."""
    return {
        output_id.lower(): pins[output_id].value() == OUTPUT_ON_LEVEL
        for output_id in OUTPUTS
    }
