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


def send_heartbeat(wlan, uptime_seconds):
    if not wlan.isconnected():
        print("Heartbeat skipped: WiFi disconnected")
        return False

    payload = {
        "firmware_version": FIRMWARE_VERSION,
        "uptime": uptime_seconds,
        "wifi_connected": True,
    }

    headers = {
        "Authorization": "Bearer " + DEVICE_TOKEN,
        "Content-Type": "application/json",
    }

    response = None

    try:
        response = requests.post(
            HEARTBEAT_URL,
            data=ujson.dumps(payload),
            headers=headers,
            timeout=10,
        )

        if response.status_code == 200:
            print("Heartbeat OK:", uptime_seconds, "s")
            return True

        print("Heartbeat failed: HTTP", response.status_code)
        try:
            print(response.text)
        except Exception:
            pass
        return False

    except Exception as exc:
        print("Heartbeat error:", exc)
        return False

    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass


def main():
    print()
    print("PoolBerry Edge Controller")
    print("Device:", DEVICE_ID)
    print("Firmware:", FIRMWARE_VERSION)

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    start = time.ticks_ms()

    while True:
        if not wlan.isconnected():
            connect_wifi(wlan)

        uptime = time.ticks_diff(time.ticks_ms(), start) // 1000

        send_heartbeat(wlan, uptime)

        time.sleep(HEARTBEAT_INTERVAL_SECONDS)


main()
