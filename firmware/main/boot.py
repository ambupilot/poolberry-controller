from machine import Pin

# Initialise the complete relay/output bank before the application, WiFi or API
# starts. Logical OFF is currently GPIO LOW for the tested relay-module input
# behavior. Physical COM/NO switching must be confirmed before loads are wired.
for gpio in range(8, 16):
    Pin(gpio, Pin.OUT, value=0)
