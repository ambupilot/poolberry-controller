import time
import network

from config import (
    DEVICE_ID,
    FIRMWARE_VERSION,
    WIFI_SSID,
    WIFI_PASSWORD,
)


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        return wlan

    print("Connecting to WiFi...")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    timeout = 20
    while not wlan.isconnected() and timeout > 0:
        print(".", end="")
        time.sleep(1)
        timeout -= 1

    print()

    if not wlan.isconnected():
        raise RuntimeError("WiFi connection failed")

    print("WiFi connected")
    print("IP address:", wlan.ifconfig()[0])
    return wlan


def main():
    print()
    print("PoolBerry Edge Controller")
    print("Device:", DEVICE_ID)
    print("Firmware:", FIRMWARE_VERSION)

    wlan = connect_wifi()
    start = time.ticks_ms()

    while True:
        uptime = time.ticks_diff(time.ticks_ms(), start) // 1000

        status = {
            "device_id": DEVICE_ID,
            "firmware_version": FIRMWARE_VERSION,
            "uptime": uptime,
            "status": "online",
            "wifi_connected": wlan.isconnected(),
        }

        print(status)
        time.sleep(10)


main()
