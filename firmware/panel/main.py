import time

from config import DEVICE_ID, FIRMWARE_VERSION


def main():
    print("PoolBerry Panel Controller")
    print("Device:", DEVICE_ID)
    print("Firmware:", FIRMWARE_VERSION)
    print("Status: ready")

    # Keep the controller alive. Button/LED handling and RS485 communication
    # will be added incrementally as the panel hardware is connected.
    while True:
        time.sleep(1)


main()
