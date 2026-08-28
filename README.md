# PoolBerry Controller

PoolBerry Controller is the concrete implementation of the PoolBerry control system.

The system consists of:

- a Raspberry Pi Pico 2 W based main edge controller;
- a separate Pico based operator panel connected over RS485;
- a VPS hosted API and control platform;
- a web application at `config.kerssing.nl`;
- persistent configuration, telemetry and event storage.

## Architecture

The system is split into two primary layers.

### Edge

The main Pico handles:

- physical I/O;
- relay and actuator control;
- temperature and flow measurement;
- local safety interlocks;
- watchdog and fail-safe behavior;
- communication with the operator panel.

### VPS

The VPS handles:

- device API;
- configuration management;
- automation and scheduling;
- telemetry storage;
- event logging;
- web interface;
- external services and notifications.

The Pico never communicates directly with the web application or database. Communication goes through the PoolBerry API.

## Repository structure

```text
firmware/
  main/       Main Pico 2 W firmware
  panel/      Operator panel Pico firmware

api/          PoolBerry API
web/          Web management application
database/     Database migrations and schema
docs/         Architecture, hardware and protocol documentation
deploy/       VPS deployment files
```

## Related repository

The higher-level architecture and design documentation is maintained separately in:

`ambupilot/PoolBerry-Platform`
