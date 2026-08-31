import time
import network
import requests
import ujson
import ubinascii
import machine
from machine import Pin
import onewire
import ds18x20

from config import (
    API_BASE_URL, CONFIG_REFRESH_INTERVAL_SECONDS, DEVICE_ID, DEVICE_TOKEN,
    FIRMWARE_VERSION, HEARTBEAT_INTERVAL_SECONDS, TELEMETRY_INTERVAL_SECONDS,
    WIFI_CONNECT_TIMEOUT_SECONDS, WIFI_PASSWORD, WIFI_SSID,
)
from outputs import initialise_outputs, output_states, set_output
from sensors import SENSORS

HEARTBEAT_URL = API_BASE_URL.rstrip("/") + "/api/v1/devices/" + DEVICE_ID + "/heartbeat"
TELEMETRY_URL = API_BASE_URL.rstrip("/") + "/api/v1/devices/" + DEVICE_ID + "/telemetry"
CONFIG_URL = API_BASE_URL.rstrip("/") + "/api/v1/devices/" + DEVICE_ID + "/config"
OUTPUT_STATE_URL = API_BASE_URL.rstrip("/") + "/api/v1/devices/" + DEVICE_ID + "/output-state"
COMMAND_URL = API_BASE_URL.rstrip("/") + "/api/v1/devices/" + DEVICE_ID + "/commands/next"
COMMAND_POLL_INTERVAL_SECONDS = 2

ONEWIRE_GPIO = 18
FLOW_F1_GPIO = 17
FLOW_F2_GPIO = 27
output_pins = initialise_outputs()
onewire_bus = onewire.OneWire(Pin(ONEWIRE_GPIO))
temperature_bus = ds18x20.DS18X20(onewire_bus)
SENSOR_BY_DEVICE_ID = {definition["device_id"].lower(): sensor_name for sensor_name, definition in SENSORS.items()}
flow_f1_pulses = 0
flow_f2_pulses = 0
flow_config = {"flow_f1_pulses_per_liter": 420.0, "flow_f2_pulses_per_liter": 420.0}


def count_f1(pin):
    global flow_f1_pulses; flow_f1_pulses += 1


def count_f2(pin):
    global flow_f2_pulses; flow_f2_pulses += 1


flow_f1_pin = Pin(FLOW_F1_GPIO, Pin.IN)
flow_f2_pin = Pin(FLOW_F2_GPIO, Pin.IN)
flow_f1_pin.irq(trigger=Pin.IRQ_FALLING, handler=count_f1)
flow_f2_pin.irq(trigger=Pin.IRQ_FALLING, handler=count_f2)


def rom_to_device_id(rom):
    family = ubinascii.hexlify(bytes([rom[0]])).decode(); serial = ubinascii.hexlify(bytes(reversed(rom[1:7]))).decode(); return family + "-" + serial


def valid_temperature(value): return value is not None and value != 85.0 and -55.0 <= value <= 125.0


def auth_headers(): return {"Authorization": "Bearer " + DEVICE_TOKEN, "Content-Type": "application/json"}


def connect_wifi(wlan):
    if not wlan.active(): wlan.active(True)
    if wlan.isconnected(): return True
    print("Connecting to WiFi..."); wlan.connect(WIFI_SSID, WIFI_PASSWORD); timeout = WIFI_CONNECT_TIMEOUT_SECONDS
    while not wlan.isconnected() and timeout > 0: time.sleep(1); timeout -= 1
    if wlan.isconnected(): print("WiFi connected:", wlan.ifconfig()[0]); return True
    print("WiFi connection failed"); return False


def post_json(url, payload):
    response = None
    try:
        response = requests.post(url, data=ujson.dumps(payload), headers=auth_headers(), timeout=10)
        if response.status_code == 200: return True
        print("POST failed: HTTP", response.status_code); return False
    except Exception as exc: print("POST error:", exc); return False
    finally:
        if response is not None:
            try: response.close()
            except Exception: pass


def refresh_config(wlan):
    if not wlan.isconnected(): return False
    response = None
    try:
        response = requests.get(CONFIG_URL, headers=auth_headers(), timeout=10)
        if response.status_code != 200: print("Config failed: HTTP", response.status_code); return False
        data = ujson.loads(response.text); f1 = float(data.get("flow_f1_pulses_per_liter", 0)); f2 = float(data.get("flow_f2_pulses_per_liter", 0))
        if f1 <= 0 or f2 <= 0: print("Config rejected: invalid flow calibration"); return False
        flow_config["flow_f1_pulses_per_liter"] = f1; flow_config["flow_f2_pulses_per_liter"] = f2
        print("Config OK: F1", f1, "p/L, F2", f2, "p/L"); return True
    except Exception as exc: print("Config error:", exc); return False
    finally:
        if response is not None:
            try: response.close()
            except Exception: pass


def poll_command(wlan):
    if not wlan.isconnected(): return False
    response = None
    try:
        response = requests.get(COMMAND_URL, headers=auth_headers(), timeout=10)
        if response.status_code != 200: print("Command poll failed: HTTP", response.status_code); return False
        data = ujson.loads(response.text)
        if data is None: return True
        output_id = str(data.get("output_id", "")).upper(); enabled = data.get("enabled")
        if output_id != "R1" or not isinstance(enabled, bool): print("Command rejected:", data); return False
        print("Command:", output_id, "ON" if enabled else "OFF")
        set_output(output_pins, output_id, enabled)
        # Report actual GPIO state before acknowledging the command.
        if not send_output_state(wlan): return False
        ack_url = API_BASE_URL.rstrip("/") + "/api/v1/devices/" + DEVICE_ID + "/commands/" + output_id + "/ack"
        if not post_json(ack_url, {}): return False
        print("Command acknowledged:", output_id); return True
    except Exception as exc: print("Command error:", exc); return False
    finally:
        if response is not None:
            try: response.close()
            except Exception: pass


def read_temperatures():
    roms = temperature_bus.scan()
    if not roms: return {}
    try: temperature_bus.convert_temp(); time.sleep_ms(750)
    except Exception as exc: print("Temperature conversion error:", exc); return {}
    readings = {}
    for rom in roms:
        device_id = rom_to_device_id(rom).lower(); sensor_name = SENSOR_BY_DEVICE_ID.get(device_id)
        if sensor_name is None: print("Unknown DS18B20:", device_id); continue
        try: value = temperature_bus.read_temp(rom)
        except Exception as exc: print(sensor_name, "read error:", exc); continue
        if not valid_temperature(value): print(sensor_name, "invalid temperature:", value); continue
        readings[sensor_name] = value
    return readings


def read_and_reset_flow(elapsed_seconds):
    global flow_f1_pulses, flow_f2_pulses
    irq_state = machine.disable_irq(); f1_pulses = flow_f1_pulses; f2_pulses = flow_f2_pulses; flow_f1_pulses = 0; flow_f2_pulses = 0; machine.enable_irq(irq_state)
    if elapsed_seconds <= 0: return 0.0, 0.0
    f1_lph = (f1_pulses * 3600.0) / (elapsed_seconds * flow_config["flow_f1_pulses_per_liter"])
    f2_lph = (f2_pulses * 3600.0) / (elapsed_seconds * flow_config["flow_f2_pulses_per_liter"])
    print("Flow F1:", f1_pulses, "pulses =", round(f1_lph, 1), "L/h"); print("Flow F2:", f2_pulses, "pulses =", round(f2_lph, 1), "L/h")
    return f1_lph, f2_lph


def send_heartbeat(wlan, uptime_seconds):
    if not wlan.isconnected(): return False
    ok = post_json(HEARTBEAT_URL, {"firmware_version": FIRMWARE_VERSION, "uptime": uptime_seconds, "wifi_connected": True})
    if ok: print("Heartbeat OK:", uptime_seconds, "s")
    return ok


def send_output_state(wlan):
    if not wlan.isconnected(): return False
    payload = output_states(output_pins); ok = post_json(OUTPUT_STATE_URL, payload)
    if ok: print("Output state OK:", payload)
    return ok


def send_telemetry(wlan, elapsed_seconds):
    if not wlan.isconnected(): return False
    readings = read_temperatures(); f1_lph, f2_lph = read_and_reset_flow(elapsed_seconds); payload = {"flow_f1_lph": f1_lph, "flow_f2_lph": f2_lph}
    for sensor_name, value in readings.items(): payload["temperature_" + sensor_name.lower() + "_c"] = value
    ok = post_json(TELEMETRY_URL, payload)
    if ok: print("Telemetry OK")
    return ok


def main():
    print(); print("PoolBerry Edge Controller"); print("Device:", DEVICE_ID); print("Firmware:", FIRMWARE_VERSION); print("Outputs: GP8-GP15"); print("1-Wire: GP" + str(ONEWIRE_GPIO)); print("Flow F1: GP" + str(FLOW_F1_GPIO)); print("Flow F2: GP" + str(FLOW_F2_GPIO))
    wlan = network.WLAN(network.STA_IF); wlan.active(True); start = time.ticks_ms(); last_heartbeat_ms = None; last_telemetry_ms = time.ticks_ms(); last_config_ms = None; last_output_state_ms = None; last_command_poll_ms = None
    while True:
        if not wlan.isconnected(): connect_wifi(wlan)
        now_ms = time.ticks_ms(); uptime = time.ticks_diff(now_ms, start) // 1000
        if last_config_ms is None or time.ticks_diff(now_ms, last_config_ms) >= CONFIG_REFRESH_INTERVAL_SECONDS * 1000: refresh_config(wlan); last_config_ms = now_ms
        if last_command_poll_ms is None or time.ticks_diff(now_ms, last_command_poll_ms) >= COMMAND_POLL_INTERVAL_SECONDS * 1000: poll_command(wlan); last_command_poll_ms = now_ms
        if last_heartbeat_ms is None or time.ticks_diff(now_ms, last_heartbeat_ms) >= HEARTBEAT_INTERVAL_SECONDS * 1000: send_heartbeat(wlan, uptime); last_heartbeat_ms = now_ms
        if last_output_state_ms is None or time.ticks_diff(now_ms, last_output_state_ms) >= HEARTBEAT_INTERVAL_SECONDS * 1000: send_output_state(wlan); last_output_state_ms = now_ms
        elapsed_ms = time.ticks_diff(now_ms, last_telemetry_ms)
        if elapsed_ms >= TELEMETRY_INTERVAL_SECONDS * 1000: send_telemetry(wlan, elapsed_ms / 1000.0); last_telemetry_ms = now_ms
        time.sleep(1)


main()
