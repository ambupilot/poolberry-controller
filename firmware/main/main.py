import time
import network
import requests
import ujson

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

# Temporary value used only to prove the telemetry path end-to-end.
SIMULATED_POOL_TEMPERATURE_C = 26.5


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

    ok = post_json(
        TELEMETRY_URL,
        {"pool_temperature_c": SIMULATED_POOL_TEMPERATURE_C},
    )

    if ok:
        print("Telemetry OK:", SIMULATED_POOL_TEMPERATURE_C, "C")
    return ok


def main():
    print()
    print("PoolBerry Edge Controller")
    print("Device:", DEVICE_ID)
    print("Firmware:", FIRMWARE_VERSION)

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
