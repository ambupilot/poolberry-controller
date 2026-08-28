import time
import network
import requests
import ujson
import ubinascii
from machine import Pin
import onewire
import ds18x20

from config import (
    API_BASE_URL,
    DEVICE_ID,
    DEVICE_TOKEN,
    FIRMWARE_VERSION,
    HEARTBEAT_INTERVAL_SECONDS,
    TELEMETRY_INTERVAL_SECONDS,
    WIFI_CONNECT_TIMEOUT_SECONDS,
    WIFI_PASSWORD,
    WIFI_SSID,
)
from sensors import SENSORS


HEARTBEAT_URL = API_BASE_URL.rstrip("/") + "/api/v1/devices/" + DEVICE_ID + "/heartbeat"
TELEMETRY_URL = API_BASE_URL.rstrip("/") + "/api/v1/devices/" + DEVICE_ID + "/telemetry"

ONEWIRE_GPIO = 18
onewire_bus = onewire.OneWire(Pin(ONEWIRE_GPIO))
temperature_bus = ds18x20.DS18X20(onewire_bus)

SENSOR_BY_DEVICE_ID = {
    definition["device_id"].lower(): sensor_name
    for sensor_name, definition in SENSORS.items()
}


def rom_to_device_id(rom):
    family = ubinascii.hexlify(bytes([rom[0]])).decode()
    serial = ubinascii.hexlify(bytes(reversed(rom[1:7]))).decode()
    return family + "-" + serial


def valid_temperature(value):
    return value is not None and value != 85.0 and -55.0 <= value <= 125.0


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
        response = requests.post(
            url,
            data=ujson.dumps(payload),
            headers={
                "Authorization": "Bearer " + DEVICE_TOKEN,
                "Content-Type": "application/json",
            },
            timeout=10,
        )
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


def read_temperatures():
    roms = temperature_bus.scan()
    if not roms:
        print("Temperature error: no DS18B20 found on GP18")
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
        print(sensor_name, SENSORS[sensor_name]["role"] + ":", value, "C")

    return readings


def send_heartbeat(wlan, uptime_seconds):
    if not wlan.isconnected():
        return False

    ok = post_json(
        HEARTBEAT_URL,
        {
            "firmware_version": FIRMWARE_VERSION,
            "uptime": uptime_seconds,
            "wifi_connected": True,
        },
    )
    if ok:
        print("Heartbeat OK:", uptime_seconds, "s")
    return ok


def send_telemetry(wlan):
    if not wlan.isconnected():
        return False

    readings = read_temperatures()
    if not readings:
        print("Telemetry skipped: no valid mapped temperatures")
        return False

    payload = {}
    for sensor_name, value in readings.items():
        payload["temperature_" + sensor_name.lower() + "_c"] = value

    ok = post_json(TELEMETRY_URL, payload)
    if ok:
        print("Telemetry OK:", payload)
    return ok


def main():
    print()
    print("PoolBerry Edge Controller")
    print("Device:", DEVICE_ID)
    print("Firmware:", FIRMWARE_VERSION)
    print("1-Wire temperature bus: GP" + str(ONEWIRE_GPIO))

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    start = time.ticks_ms()
    last_heartbeat_ms = None
    last_telemetry_ms = None

    while True:
        if not wlan.isconnected():
            connect_wifi(wlan)

        now_ms = time.ticks_ms()
        uptime = time.ticks_diff(now_ms, start) // 1000

        if last_heartbeat_ms is None or time.ticks_diff(now_ms, last_heartbeat_ms) >= HEARTBEAT_INTERVAL_SECONDS * 1000:
            send_heartbeat(wlan, uptime)
            last_heartbeat_ms = now_ms

        if last_telemetry_ms is None or time.ticks_diff(now_ms, last_telemetry_ms) >= TELEMETRY_INTERVAL_SECONDS * 1000:
            send_telemetry(wlan)
            last_telemetry_ms = now_ms

        time.sleep(1)


main()
