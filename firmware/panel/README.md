# PoolBerry Panel Controller

## Purpose

The PANEL controller is a Raspberry Pi Pico 2 without WiFi. It provides the physical operator panel for PoolBerry and communicates directly with the MAIN controller over RS485.

The PANEL is an input/output interface only. It does not control relays directly and does not contain independent pool process or safety logic. MAIN remains authoritative for operating mode, interlocks, command acceptance, transitions and actual state.

## Pico GPIO allocation

| Pico GPIO | Function |
|---|---|
| GP0 | I2C SDA |
| GP1 | I2C SCL |
| GP4 | RS485 TX -> MAX3485 DI |
| GP5 | RS485 RX <- MAX3485 RO |
| GP6 | RS485 DE + /RE |
| Other GPIO | Reserved/free |

## I2C devices

| Device | Address | Function |
|---|---:|---|
| MCP23017 #1 | `0x20` | 12 push buttons (inputs) |
| MCP23017 #2 | `0x21` | 12 panel LEDs (outputs) |

The remaining four GPIOs on each MCP23017 are reserved.

## Button mapping - MCP23017 #1 (`0x20`)

| MCP pin | Button | Panel function | Semantic command |
|---|---|---|---|
| GPA0 | K1 | Filterpomp AAN | `FILTERPUMP_ON` |
| GPA1 | K2 | Filterpomp UIT | `FILTERPUMP_OFF` |
| GPA2 | K3 | Warmtepomp AAN | `HEATPUMP_ON` |
| GPA3 | K4 | Warmtepomp UIT | `HEATPUMP_OFF` |
| GPA4 | K5 | Collector OPEN | `COLLECTOR_OPEN` |
| GPA5 | K6 | Collector DICHT | `COLLECTOR_CLOSE` |
| GPA6 | K7 | Bronpomp AAN | `SOURCEPUMP_ON` |
| GPA7 | K8 | Bronpomp UIT | `SOURCEPUMP_OFF` |
| GPB0 | K9 | AUTO | `PROGRAM_AUTO` |
| GPB1 | K10 | SPOELEN | `PROGRAM_BACKWASH` |
| GPB2 | K11 | SPROEIEN | `PROGRAM_IRRIGATION` |
| GPB3 | K12 | STOP | `STOP` |
| GPB4-GPB7 | - | Reserved | - |

## LED mapping - MCP23017 #2 (`0x21`)

| MCP pin | LED | Indication |
|---|---|---|
| GPA0 | H1 | Filterpomp AAN |
| GPA1 | H2 | Filterpomp UIT |
| GPA2 | H3 | Warmtepomp AAN |
| GPA3 | H4 | Warmtepomp UIT |
| GPA4 | H5 | Collector OPEN |
| GPA5 | H6 | Collector DICHT |
| GPA6 | H7 | Bronpomp AAN |
| GPA7 | H8 | Bronpomp UIT |
| GPB0 | H9 | AUTO |
| GPB1 | H10 | SPOELEN |
| GPB2 | H11 | SPROEIEN |
| GPB3 | H12 | STOP |
| GPB4-GPB7 | - | Reserved |

## Control model

Buttons send semantic commands to MAIN. PANEL never translates a button press directly into a relay state.

Example:

```text
K1 pressed
  -> PANEL sends FILTERPUMP_ON
  -> MAIN validates controller mode and interlocks
  -> MAIN accepts or rejects the command
  -> MAIN reports authoritative operational state
  -> PANEL renders that state on H1/H2
```

RS485 messages must therefore use semantic operations such as `FILTERPUMP_ON`, `COLLECTOR_OPEN` and `STOP`, rather than hardware identifiers such as K1, H1 or R1.

This keeps web control and physical panel control on the same MAIN-side command and safety model.

## LED behaviour

Normal LED behaviour:

- LED continuously ON: corresponding confirmed state is active.
- LED blinking: corresponding transition/action is in progress.
- LED OFF: corresponding state is not active.

A requested state is not considered confirmed merely because the button was pressed. MAIN is the source of truth for the state rendered by PANEL.

## NORMAL mode

In `NORMAL` mode, K1-K12 may send their defined semantic commands. MAIN decides whether an operational command is allowed and reports the resulting state back to PANEL.

STOP remains available at all times.

## MANUAL mode

`MANUAL` is a global MAIN controller mode, not a local PANEL mode.

When MAIN reports `MANUAL`:

- K1-K11 are disabled and must not initiate operational commands.
- H1-H11 are OFF regardless of the underlying relay/output states.
- K12 STOP remains active.
- H12 STOP **blinks continuously** for the entire time MANUAL is active.

The blinking STOP LED is the visual indication on the physical panel that the controller is in an exceptional/manual operating mode and that normal panel operation is disabled.

PANEL must not infer MANUAL locally; it renders the mode reported by MAIN.

When MAIN returns to `NORMAL`, PANEL must refresh/resynchronise the authoritative controller state before restoring the normal H1-H11 indications. H12 then returns to its normal STOP indication behaviour.

## STOP

STOP is a semantic command and remains usable in both `NORMAL` and `MANUAL` mode.

The physical panel STOP button is a software/controller STOP and is not a substitute for a future hardwired emergency stop.

## RS485

Planned transceiver: MAX3485 (3.3 V).

Planned connection on PANEL:

```text
Pico 3V3 -> MAX3485 VCC
Pico GND -> MAX3485 GND
GP4 TX   -> MAX3485 DI
GP5 RX   <- MAX3485 RO
GP6      -> MAX3485 DE and /RE
```

Direction control:

- GP6 LOW: receive
- GP6 HIGH: transmit

Between MAIN and PANEL:

```text
A   <-> A
B   <-> B
GND <-> GND
```

The first hardware communication test will be a minimal request/response exchange (`PING` / `PONG`) before the operational semantic protocol is implemented.
