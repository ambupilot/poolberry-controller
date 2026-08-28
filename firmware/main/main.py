import time
import network
import requests
import ujson
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


HEARTBEAT_URL = (
    API_BASE_URL.rstrip("/")
    + "/api/v1/devices/"
    + DEVICE_ID
    + "/heartbeat"
)
TELEMETRY_URL = (
    API_BASE_URL.rstrip("/")
    + "/api/v1/devices/"
    + DEVICE_ID
    + "/telemetry"
)

# PoolBerry 1-Wire temperature bus.
# All DS18B20 temperature sensors will eventually share GP18.
ONEWIRE_GPIO = 18

onewire_bus = onewire.OneWire(Pin(ONEWIRE_GPIO))
temperature_bus = ds18x20.DS18X20(onewire_bus)


def connect_wifi(wlan):
    if not wlan.active():
        wlan.active(True)

    if wlan.isconnected():
        return True

    print("Connecting to WiFi...")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    timeout = WIFI_CONNECT_TIMEOUT_SECONDS
    while not wlan.isconnected() and timeout > 0:
        print(".", end="")
        time.sleep(1)
        timeout -= 1

    print()

    if wlan.isconnected():
        print("WiFi connected")
        print("IP address:", wlan.ifconfig()[0])
        return True

    print("WiFi connection failed")
    return False


def post_json(url, payload):
    headers = {
        "Authorization": "Bearer " + DEVICE_TOKEN,
        "Content-Type": "application/json",
    }

    response = None
    try:
        response = requests.post(
            url,
            data=ujson.dumps(payload),
            headers=headers,
            timeout=10,
        )
        if response.status_code == 200:
            return True

        print("POST failed: HTTP", response.status_code)
        try:
            print(response.text)
        except Exception:
            pass
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


def read_pool_temperature():
    roms = temperature_bus.scan()

    if not roms:
        print("Temperature error: no DS18B20 found on GP18")
        return None

    # During this first hardware phase the single connected DS18B20 is T2 / pool.
    # Once all six sensors are installed this will be replaced by fixed ROM mapping.
    rom = roms[0]

    try:
        temperature_bus.convert_temp()
        time.sleep_ms(750)
        temperature = temperature_bus.read_temp(rom)
    except Exception as exc:
        print("Temperature read error:", exc)
        return None

    # Reject known DS18B20 power-up/error value and impossible readings.
    if temperature is None or temperature == 85.0:
        print("Temperature error: invalid reading", temperature)
        return None

    if temperature < -55.0 or temperature > 125.0:
        print("Temperature error: out of range", temperature)
        return None

    return temperature


def send_heartbeat(wlan, uptime_seconds):
    if not wlan.isconnected():
        print("Heartbeat skipped: WiFi disconnected")
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
        print("Telemetry skipped: WiFi disconnected")
        return False

    pool_temperature = read_pool_temperature()
    if pool_temperature is None:
        print("Telemetry skipped: no valid pool temperature")
        return False

    ok = post_json(
        TELEMETRY_URL,
        {"pool_temperature_c": pool_temperature},
    )

    if ok:
        print("Telemetry OK:", pool_temperature, "C")
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

        if (
            last_heartbeat_ms is None
            or time.ticks_diff(now_ms, last_heartbeat_ms)
            >= HEARTBEAT_INTERVAL_SECONDS * 1000
        ):
            send_heartbeat(wlan, uptime)
            last_heartbeat_ms = now_ms

        if (
            last_telemetry_ms is None
            or time.ticks_diff(now_ms, last_telemetry_ms)
            >= TELEMETRY_INTERVAL_SECONDS * 1000
        ):
            send_telemetry(wlan)
            last_telemetry_ms = now_ms

        time.sleep(1)


main()
