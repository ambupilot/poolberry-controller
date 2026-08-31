import time
import network
import requests
import ujson
import ubinascii
import machine
from machine import Pin
import onewire
import ds18x20

from config import (API_BASE_URL, CONFIG_REFRESH_INTERVAL_SECONDS, DEVICE_ID, DEVICE_TOKEN, FIRMWARE_VERSION, HEARTBEAT_INTERVAL_SECONDS, TELEMETRY_INTERVAL_SECONDS, WIFI_CONNECT_TIMEOUT_SECONDS, WIFI_PASSWORD, WIFI_SSID)
from outputs import OUTPUTS, all_outputs_off, initialise_outputs, output_states, set_output
from sensors import SENSORS

HEARTBEAT_URL = API_BASE_URL.rstrip("/") + "/api/v1/devices/" + DEVICE_ID + "/heartbeat"
TELEMETRY_URL = API_BASE_URL.rstrip("/") + "/api/v1/devices/" + DEVICE_ID + "/telemetry"
CONFIG_URL = API_BASE_URL.rstrip("/") + "/api/v1/devices/" + DEVICE_ID + "/config"
OUTPUT_STATE_URL = API_BASE_URL.rstrip("/") + "/api/v1/devices/" + DEVICE_ID + "/output-state"
COMMAND_URL = API_BASE_URL.rstrip("/") + "/api/v1/devices/" + DEVICE_ID + "/commands/next"
COMMAND_POLL_INTERVAL_SECONDS = 2
FILTERPUMP_SHUTDOWN_DELAY_SECONDS = 5
COLLECTOR_OPEN_DELAY_SECONDS = 10
COLLECTOR_CLOSE_DELAY_SECONDS = 15
ONEWIRE_GPIO = 18
FLOW_F1_GPIO = 17
FLOW_F2_GPIO = 27

output_pins = initialise_outputs()
onewire_bus = onewire.OneWire(Pin(ONEWIRE_GPIO))
temperature_bus = ds18x20.DS18X20(onewire_bus)
SENSOR_BY_DEVICE_ID = {definition["device_id"].lower(): sensor_name for sensor_name, definition in SENSORS.items()}
flow_f1_pulses = 0
flow_f2_pulses = 0
flow_config = {
    "flow_f1_pulses_per_liter": 420.0,
    "flow_f2_pulses_per_liter": 420.0,
    "filter_flow_safety_bypass": True,
    "filter_min_flow_lph": 500.0,
    "filter_flow_grace_seconds": 10,
}
filter_operation_started_ms = None
active_sequence = None


def count_f1(pin):
    global flow_f1_pulses
    flow_f1_pulses += 1


def count_f2(pin):
    global flow_f2_pulses
    flow_f2_pulses += 1


flow_f1_pin = Pin(FLOW_F1_GPIO, Pin.IN)
flow_f2_pin = Pin(FLOW_F2_GPIO, Pin.IN)
flow_f1_pin.irq(trigger=Pin.IRQ_FALLING, handler=count_f1)
flow_f2_pin.irq(trigger=Pin.IRQ_FALLING, handler=count_f2)


def rom_to_device_id(rom):
    family = ubinascii.hexlify(bytes([rom[0]])).decode()
    serial = ubinascii.hexlify(bytes(reversed(rom[1:7]))).decode()
    return family + "-" + serial


def valid_temperature(value):
    return value is not None and value != 85.0 and -55.0 <= value <= 125.0


def auth_headers():
    return {"Authorization": "Bearer " + DEVICE_TOKEN, "Content-Type": "application/json"}


def connect_wifi(wlan):
    if not wlan.active():
        wlan.active(True)
    if wlan.isconnected():
        return True
    print("Connecting to WiFi...")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    timeout = WIFI_CONNECT_TIMEOUT_SECONDS
    while not wlan.isconnected() and timeout > 0:
        time.sleep(1)
        timeout -= 1
    if wlan.isconnected():
        print("WiFi connected:", wlan.ifconfig()[0])
        return True
    print("WiFi connection failed")
    return False


def post_json(url, payload):
    response = None
    try:
        response = requests.post(url, data=ujson.dumps(payload), headers=auth_headers(), timeout=10)
        if response.status_code == 200:
            return True
        print("POST failed: HTTP", response.status_code)
        return False
    except Exception as exc:
        print("POST error:", exc)
        return False
    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass


def refresh_config(wlan):
    if not wlan.isconnected():
        return False
    response = None
    try:
        response = requests.get(CONFIG_URL, headers=auth_headers(), timeout=10)
        if response.status_code != 200:
            print("Config failed: HTTP", response.status_code)
            return False
        data = ujson.loads(response.text)
        f1 = float(data.get("flow_f1_pulses_per_liter", 0))
        f2 = float(data.get("flow_f2_pulses_per_liter", 0))
        if f1 <= 0 or f2 <= 0:
            print("Config rejected: invalid flow calibration")
            return False
        flow_config["flow_f1_pulses_per_liter"] = f1
        flow_config["flow_f2_pulses_per_liter"] = f2
        flow_config["filter_flow_safety_bypass"] = bool(data.get("filter_flow_safety_bypass", True))
        flow_config["filter_min_flow_lph"] = float(data.get("filter_min_flow_lph", 500.0))
        flow_config["filter_flow_grace_seconds"] = int(data.get("filter_flow_grace_seconds", 10))
        print("Config OK: F1", f1, "p/L, F2", f2, "p/L, flow bypass", flow_config["filter_flow_safety_bypass"])
        return True
    except Exception as exc:
        print("Config error:", exc)
        return False
    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass


def acknowledge_command(command_id):
    return post_json(API_BASE_URL.rstrip("/") + "/api/v1/devices/" + DEVICE_ID + "/commands/" + command_id + "/ack", {})


def send_output_state(wlan):
    if not wlan.isconnected():
        return False
    payload = output_states(output_pins)
    ok = post_json(OUTPUT_STATE_URL, payload)
    if ok:
        print("Output state OK:", payload)
    return ok


def apply_output_actions(actions):
    for output_id, enabled in actions:
        set_output(output_pins, output_id, enabled)


def finish_sequence(name):
    global active_sequence, filter_operation_started_ms
    print("Sequence complete:", name)
    if name == "FILTERPUMP_OFF":
        filter_operation_started_ms = None
    active_sequence = None


def cancel_sequence(reason):
    global active_sequence
    if active_sequence is not None:
        print("Sequence cancelled:", active_sequence["name"], "-", reason)
    active_sequence = None


def start_sequence(name, steps, wlan, abort_actions=None):
    global active_sequence
    if active_sequence is not None:
        print("Sequence rejected:", name, "because", active_sequence["name"], "is active")
        return False
    active_sequence = {
        "name": name,
        "steps": steps,
        "index": 0,
        "due_ms": time.ticks_ms(),
        "abort_actions": abort_actions or (),
    }
    print("Sequence started:", name)
    update_sequence(wlan)
    return True


def abort_active_sequence(wlan, reason):
    global active_sequence
    if active_sequence is None:
        return
    name = active_sequence["name"]
    abort_actions = active_sequence.get("abort_actions", ())
    print("Sequence abort:", name, "-", reason)
    if abort_actions:
        apply_output_actions(abort_actions)
        send_output_state(wlan)
    active_sequence = None


def update_sequence(wlan):
    global active_sequence
    if active_sequence is None:
        return

    now_ms = time.ticks_ms()
    if time.ticks_diff(now_ms, active_sequence["due_ms"]) < 0:
        return

    steps = active_sequence["steps"]
    index = active_sequence["index"]
    if index >= len(steps):
        finish_sequence(active_sequence["name"])
        return

    step = steps[index]
    if step.get("requires_r1") and not output_states(output_pins)["r1"]:
        abort_active_sequence(wlan, "filter pump is OFF")
        return

    actions = step.get("actions", ())
    if actions:
        apply_output_actions(actions)
    message = step.get("message")
    if message:
        print(message)
    if actions:
        send_output_state(wlan)

    active_sequence["index"] = index + 1
    next_index = index + 1
    if next_index >= len(steps):
        finish_sequence(active_sequence["name"])
        return

    delay_seconds = steps[next_index].get("delay_seconds", 0)
    active_sequence["due_ms"] = time.ticks_add(now_ms, int(delay_seconds * 1000))


def execute_filterpump_on(wlan):
    global filter_operation_started_ms
    if active_sequence is not None:
        print("FILTERPUMP_ON rejected locally: sequence active")
        return False
    states = output_states(output_pins)
    if states["r4"] or states["r8"]:
        print("FILTERPUMP_ON rejected locally: pool route is not open")
        return False
    set_output(output_pins, "R1", True)
    filter_operation_started_ms = time.ticks_ms()
    print("FILTERPUMP_ON: R1 ON")
    return send_output_state(wlan)


def execute_collector_open(wlan):
    if active_sequence is not None:
        print("COLLECTOR_OPEN rejected locally: sequence active")
        return False
    states = output_states(output_pins)
    if not states["r1"]:
        print("COLLECTOR_OPEN rejected locally: filter pump is OFF")
        return False
    return start_sequence(
        "COLLECTOR_OPEN",
        [
            {
                "delay_seconds": 0,
                "actions": (("R7", True),),
                "message": "COLLECTOR_OPEN: R7 ON - collector route opening",
            },
            {
                "delay_seconds": COLLECTOR_OPEN_DELAY_SECONDS,
                "requires_r1": True,
                "actions": (("R8", True),),
                "message": "COLLECTOR_OPEN: R8 ON - bypass closed",
            },
        ],
        wlan,
        abort_actions=(("R7", False), ("R8", False)),
    )


def execute_collector_close(wlan):
    if active_sequence is not None:
        print("COLLECTOR_CLOSE rejected locally: sequence active")
        return False
    return start_sequence(
        "COLLECTOR_CLOSE",
        [
            {
                "delay_seconds": 0,
                "actions": (("R8", False),),
                "message": "COLLECTOR_CLOSE: R8 OFF - normal route opening",
            },
            {
                "delay_seconds": COLLECTOR_CLOSE_DELAY_SECONDS,
                "actions": (("R7", False),),
                "message": "COLLECTOR_CLOSE: R7 OFF - collector route closed",
            },
        ],
        wlan,
    )


def execute_filterpump_off(wlan):
    if active_sequence is not None:
        print("FILTERPUMP_OFF rejected locally: sequence active")
        return False

    states = output_states(output_pins)
    collector_active = states["r7"] or states["r8"]
    collector_delay = COLLECTOR_CLOSE_DELAY_SECONDS if collector_active else 0

    return start_sequence(
        "FILTERPUMP_OFF",
        [
            {
                "delay_seconds": 0,
                "actions": (
                    ("R2", False),
                    ("R3", False),
                    ("R4", False),
                    ("R5", False),
                    ("R6", False),
                    ("R8", False),
                ),
                "message": "FILTERPUMP_OFF: dependent outputs OFF; normal collector route open",
            },
            {
                "delay_seconds": collector_delay,
                "actions": (("R7", False),),
                "message": "FILTERPUMP_OFF: collector route closed",
            },
            {
                "delay_seconds": FILTERPUMP_SHUTDOWN_DELAY_SECONDS,
                "actions": (("R1", False),),
                "message": "FILTERPUMP_OFF: R1 OFF after safe shutdown sequence",
            },
        ],
        wlan,
    )


def execute_heatpump_on(wlan):
    if active_sequence is not None:
        print("HEATPUMP_ON rejected locally: sequence active")
        return False
    states = output_states(output_pins)
    if not states["r1"]:
        print("HEATPUMP_ON rejected locally: filter pump is OFF")
        return False
    set_output(output_pins, "R2", True)
    print("HEATPUMP_ON: R2 ON")
    return send_output_state(wlan)


def execute_heatpump_off(wlan):
    if active_sequence is not None:
        print("HEATPUMP_OFF rejected locally: sequence active")
        return False
    set_output(output_pins, "R2", False)
    print("HEATPUMP_OFF: R2 OFF, R1 unchanged")
    return send_output_state(wlan)


def sourcepump_route_valid(states):
    garden_open = not states["r6"]
    source_to_pool_open = states["r5"]
    return (garden_open or source_to_pool_open) and (not source_to_pool_open or states["r4"])


def execute_sourcepump_on(wlan):
    if active_sequence is not None:
        print("SOURCEPUMP_ON rejected locally: sequence active")
        return False
    states = output_states(output_pins)
    if not sourcepump_route_valid(states):
        print("SOURCEPUMP_ON rejected locally: unsafe valve route R4/R5/R6")
        return False
    set_output(output_pins, "R3", True)
    print("SOURCEPUMP_ON: R3 ON; valves unchanged")
    return send_output_state(wlan)


def execute_sourcepump_off(wlan):
    if active_sequence is not None:
        print("SOURCEPUMP_OFF rejected locally: sequence active")
        return False
    set_output(output_pins, "R3", False)
    print("SOURCEPUMP_OFF: R3 OFF; valves unchanged")
    return send_output_state(wlan)


def poll_command(wlan):
    global filter_operation_started_ms
    if not wlan.isconnected():
        return False
    response = None
    try:
        response = requests.get(COMMAND_URL, headers=auth_headers(), timeout=10)
        if response.status_code != 200:
            print("Command poll failed: HTTP", response.status_code)
            return False
        data = ujson.loads(response.text)
        if data is None:
            return True

        command_id = str(data.get("output_id", "")).upper()
        enabled = data.get("enabled")

        if command_id == "STOP":
            print("Command: STOP - cancelling sequence and switching all outputs OFF")
            cancel_sequence("STOP")
            all_outputs_off(output_pins)
            filter_operation_started_ms = None
            if not send_output_state(wlan):
                return False
            if not acknowledge_command("STOP"):
                return False
            print("Command acknowledged: STOP")
            return True

        if active_sequence is not None:
            print("Command deferred while sequence active:", command_id, "during", active_sequence["name"])
            return True

        handlers = {
            "FILTERPUMP_ON": execute_filterpump_on,
            "FILTERPUMP_OFF": execute_filterpump_off,
            "HEATPUMP_ON": execute_heatpump_on,
            "HEATPUMP_OFF": execute_heatpump_off,
            "COLLECTOR_OPEN": execute_collector_open,
            "COLLECTOR_CLOSE": execute_collector_close,
            "SOURCEPUMP_ON": execute_sourcepump_on,
            "SOURCEPUMP_OFF": execute_sourcepump_off,
        }
        if command_id in handlers:
            if not handlers[command_id](wlan):
                return False
            if not acknowledge_command(command_id):
                return False
            print("Command acknowledged:", command_id)
            return True

        if command_id not in OUTPUTS or not isinstance(enabled, bool):
            print("Command rejected:", data)
            return False

        print("Command:", command_id, "ON" if enabled else "OFF")
        set_output(output_pins, command_id, enabled)
        if command_id == "R1":
            filter_operation_started_ms = None
        if not send_output_state(wlan):
            return False
        if not acknowledge_command(command_id):
            return False
        print("Command acknowledged:", command_id)
        return True
    except Exception as exc:
        print("Command error:", exc)
        return False
    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass


def read_temperatures():
    roms = temperature_bus.scan()
    if not roms:
        return {}
    try:
        temperature_bus.convert_temp()
        time.sleep_ms(750)
    except Exception as exc:
        print("Temperature conversion error:", exc)
        return {}
    readings = {}
    for rom in roms:
        device_id = rom_to_device_id(rom).lower()
        sensor_name = SENSOR_BY_DEVICE_ID.get(device_id)
        if sensor_name is None:
            print("Unknown DS18B20:", device_id)
            continue
        try:
            value = temperature_bus.read_temp(rom)
        except Exception as exc:
            print(sensor_name, "read error:", exc)
            continue
        if not valid_temperature(value):
            print(sensor_name, "invalid temperature:", value)
            continue
        readings[sensor_name] = value
    return readings


def read_and_reset_flow(elapsed_seconds):
    global flow_f1_pulses, flow_f2_pulses
    irq_state = machine.disable_irq()
    f1_pulses = flow_f1_pulses
    f2_pulses = flow_f2_pulses
    flow_f1_pulses = 0
    flow_f2_pulses = 0
    machine.enable_irq(irq_state)
    if elapsed_seconds <= 0:
        return 0.0, 0.0
    f1_lph = (f1_pulses * 3600.0) / (elapsed_seconds * flow_config["flow_f1_pulses_per_liter"])
    f2_lph = (f2_pulses * 3600.0) / (elapsed_seconds * flow_config["flow_f2_pulses_per_liter"])
    print("Flow F1:", f1_pulses, "pulses =", round(f1_lph, 1), "L/h")
    print("Flow F2:", f2_pulses, "pulses =", round(f2_lph, 1), "L/h")
    return f1_lph, f2_lph


def enforce_filter_flow_safety(wlan, f1_lph, f2_lph):
    global filter_operation_started_ms
    if filter_operation_started_ms is None or flow_config["filter_flow_safety_bypass"]:
        return True
    if not output_states(output_pins)["r1"]:
        filter_operation_started_ms = None
        return True
    running_seconds = time.ticks_diff(time.ticks_ms(), filter_operation_started_ms) / 1000.0
    if running_seconds < flow_config["filter_flow_grace_seconds"]:
        return True
    total_flow = f1_lph + f2_lph
    if total_flow >= flow_config["filter_min_flow_lph"]:
        return True
    print("FLOW SAFETY STOP: total flow", round(total_flow, 1), "L/h below", flow_config["filter_min_flow_lph"], "L/h")
    cancel_sequence("flow safety stop")
    all_outputs_off(output_pins)
    filter_operation_started_ms = None
    return send_output_state(wlan)


def send_heartbeat(wlan, uptime_seconds):
    if not wlan.isconnected():
        return False
    ok = post_json(HEARTBEAT_URL, {"firmware_version": FIRMWARE_VERSION, "uptime": uptime_seconds, "wifi_connected": True})
    if ok:
        print("Heartbeat OK:", uptime_seconds, "s")
    return ok


def send_telemetry(wlan, elapsed_seconds):
    if not wlan.isconnected():
        return False
    readings = read_temperatures()
    f1_lph, f2_lph = read_and_reset_flow(elapsed_seconds)
    payload = {"flow_f1_lph": f1_lph, "flow_f2_lph": f2_lph}
    for sensor_name, value in readings.items():
        payload["temperature_" + sensor_name.lower() + "_c"] = value
    ok = post_json(TELEMETRY_URL, payload)
    if ok:
        print("Telemetry OK")
    if not enforce_filter_flow_safety(wlan, f1_lph, f2_lph):
        return False
    return ok


def main():
    print()
    print("PoolBerry Edge Controller")
    print("Device:", DEVICE_ID)
    print("Firmware:", FIRMWARE_VERSION)
    print("Outputs: GP8-GP15")
    print("1-Wire: GP" + str(ONEWIRE_GPIO))
    print("Flow F1: GP" + str(FLOW_F1_GPIO))
    print("Flow F2: GP" + str(FLOW_F2_GPIO))
    print("Valve sequencer: non-blocking")

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    start = time.ticks_ms()
    last_heartbeat_ms = None
    last_telemetry_ms = time.ticks_ms()
    last_config_ms = None
    last_output_state_ms = None
    last_command_poll_ms = None

    while True:
        if not wlan.isconnected():
            connect_wifi(wlan)

        now_ms = time.ticks_ms()
        uptime = time.ticks_diff(now_ms, start) // 1000

        update_sequence(wlan)

        if last_config_ms is None or time.ticks_diff(now_ms, last_config_ms) >= CONFIG_REFRESH_INTERVAL_SECONDS * 1000:
            refresh_config(wlan)
            last_config_ms = now_ms

        if last_command_poll_ms is None or time.ticks_diff(now_ms, last_command_poll_ms) >= COMMAND_POLL_INTERVAL_SECONDS * 1000:
            poll_command(wlan)
            last_command_poll_ms = now_ms

        if last_heartbeat_ms is None or time.ticks_diff(now_ms, last_heartbeat_ms) >= HEARTBEAT_INTERVAL_SECONDS * 1000:
            send_heartbeat(wlan, uptime)
            last_heartbeat_ms = now_ms

        if last_output_state_ms is None or time.ticks_diff(now_ms, last_output_state_ms) >= HEARTBEAT_INTERVAL_SECONDS * 1000:
            send_output_state(wlan)
            last_output_state_ms = now_ms

        elapsed_ms = time.ticks_diff(now_ms, last_telemetry_ms)
        if elapsed_ms >= TELEMETRY_INTERVAL_SECONDS * 1000:
            send_telemetry(wlan, elapsed_ms / 1000.0)
            last_telemetry_ms = now_ms

        time.sleep(0.2)


main()
