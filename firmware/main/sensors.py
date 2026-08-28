# Fixed PoolBerry DS18B20 mapping migrated from the previous controller.
# device_id uses the Linux 1-Wire representation: family-serial.

SENSORS = {
    "T1": {
        "device_id": "28-000000259db4",
        "role": "BUITEN",
    },
    "T2": {
        "device_id": "28-00000075ea14",
        "role": "ZWEMBAD",
    },
    "T3": {
        "device_id": "28-000000cb1f60",
        "role": "WARMTEPOMP",
    },
    "T4": {
        "device_id": "28-0000007650b8",
        "role": "COLLECTOR",
    },
    "T5": {
        "device_id": "28-000000751cde",
        "role": "ZWEMBAD IN",
    },
    "T6": {
        "device_id": "28-0000001554a9",
        "role": "BINNEN",
    },
}
