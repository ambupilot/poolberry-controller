from machine import Pin

# Initialise the complete relay/output bank before the application, WiFi or API
# starts. The relay module is active-low:
# GPIO HIGH -> relay de-energised -> logical OFF
# GPIO LOW  -> relay energised   -> logical ON
#
# Force every output HIGH as early as possible during MicroPython startup so
# application startup cannot briefly energise the relays.
for gpio in range(8, 16):
    Pin(gpio, Pin.OUT, value=1)
