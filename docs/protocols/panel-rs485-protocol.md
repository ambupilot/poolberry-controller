# PoolBerry PANEL <-> MAIN RS485 Protocol

Status: design baseline; transport implementation deferred until MAX3485 hardware is available.

## 1. Purpose

This protocol connects the physical PoolBerry PANEL controller to the MAIN controller over a half-duplex RS485 link.

PANEL is an operator interface only. MAIN remains authoritative for controller mode, safety/interlocks, command acceptance, process transitions and actual operational state.

The protocol is semantic: messages describe requested operations and controller state. Hardware identifiers such as K1, H1 or R1 are never part of the control contract.

## 2. Physical transport

Planned hardware on both controllers: MAX3485, 3.3 V.

Reserved Pico GPIO:

- GP4: UART TX
- GP5: UART RX
- GP6: MAX3485 DE and /RE direction control
- GP6 LOW: receive
- GP6 HIGH: transmit

Bus wiring:

```text
MAIN A   <-> PANEL A
MAIN B   <-> PANEL B
MAIN GND <-> PANEL GND
```

Exact UART baud rate, framing, termination and biasing will be confirmed during the first hardware tests.

## 3. Communication model

The link is point-to-point between one MAIN and one PANEL.

MAIN is the authority. PANEL may request operations, but a local button press never implies that an operation succeeded.

Normal flow:

```text
PANEL button
    -> semantic command request
    -> MAIN validates mode and interlocks
    -> MAIN accepts or rejects request
    -> MAIN performs/starts operation
    -> MAIN publishes authoritative state
    -> PANEL renders LEDs from that state
```

## 4. Message framing

Version 1 uses human-readable, newline-terminated ASCII messages. This makes initial commissioning and diagnostics possible through UART/USB tools.

Conceptual format:

```text
TYPE|ID|PAYLOAD\n
```

Fields must not contain `|`, carriage return or newline characters.

`ID` is a monotonically increasing PANEL-generated command/request identifier where correlation is required.

The exact parser, maximum frame length and optional integrity check will be finalised after physical RS485 testing.

## 5. Initial link test

Before operational commands are implemented, the first MAX3485 test is:

```text
MAIN  -> PANEL: PING|42
PANEL -> MAIN:  PONG|42
```

This test verifies UART configuration, MAX3485 direction control and the physical A/B link without involving pool-control logic.

## 6. PANEL command requests

Operational commands from PANEL use semantic names.

Defined commands:

```text
FILTERPUMP_ON
FILTERPUMP_OFF
HEATPUMP_ON
HEATPUMP_OFF
COLLECTOR_OPEN
COLLECTOR_CLOSE
SOURCEPUMP_ON
SOURCEPUMP_OFF
PROGRAM_AUTO
PROGRAM_BACKWASH
PROGRAM_IRRIGATION
STOP
```

Conceptual request:

```text
CMD|101|FILTERPUMP_ON
```

The command identifier allows PANEL to correlate MAIN's response with the button action that caused it.

## 7. Command acceptance and rejection

MAIN must explicitly accept or reject a command request.

Examples:

```text
ACK|101|FILTERPUMP_ON
```

```text
REJECT|101|FILTERPUMP_ON|MANUAL_MODE
```

Possible rejection reasons will be centrally defined by MAIN. PANEL may use the reason for diagnostics, but must not duplicate the underlying safety/interlock logic.

An ACK means MAIN accepted the request for processing. It does not by itself mean the requested final physical state has already been reached.

## 8. Authoritative state

MAIN publishes state independently of command acknowledgement.

State messages must cover at least:

- controller mode: `NORMAL` or `MANUAL`
- filter pump operational state
- heat pump operational state
- collector operational state
- source pump operational state
- selected/active program state
- transition/in-progress state where required for LED blinking
- STOP state/indication where applicable

Conceptual examples:

```text
STATE|MODE|NORMAL
STATE|FILTERPUMP|ON
STATE|COLLECTOR|OPEN
STATE|COLLECTOR|OPENING
```

PANEL LEDs are rendered from authoritative MAIN state, not directly from button presses or ACK messages.

## 9. Transition indication

MAIN must expose enough transition information for PANEL to distinguish a stable state from an operation in progress.

Examples:

```text
STATE|COLLECTOR|OPENING
STATE|COLLECTOR|OPEN
```

PANEL may render:

- stable confirmed state: LED continuously ON
- transition toward state: corresponding LED blinking
- inactive state: LED OFF

PANEL does not calculate hydraulic timing itself.

## 10. NORMAL mode

In `NORMAL`, PANEL may send all defined operational commands.

MAIN remains responsible for deciding whether each command is allowed.

STOP remains available.

## 11. MANUAL mode

`MANUAL` is a global MAIN controller mode.

When PANEL receives authoritative state:

```text
STATE|MODE|MANUAL
```

PANEL must immediately enter its MANUAL presentation state:

- K1-K11 do not send operational commands.
- H1-H11 are forced OFF.
- K12 STOP remains active.
- H12 STOP blinks continuously while MANUAL remains active.

The blinking STOP LED is the physical-panel indication that normal panel operation is disabled because the controller is in MANUAL mode.

PANEL must not infer or enter MANUAL independently.

When MAIN returns to `NORMAL`, PANEL must resynchronise authoritative state before restoring normal H1-H11 indications.

## 12. STOP priority

STOP is valid in both `NORMAL` and `MANUAL`.

PANEL must be able to transmit `STOP` even when all other operational buttons are disabled.

MAIN must treat STOP as the highest-priority semantic operation. A lower-priority pending operation must never cancel or supersede STOP.

The RS485 STOP command is a software/controller STOP. It is not a replacement for a future hardwired emergency stop.

## 13. Synchronisation and reconnect

PANEL must not assume that its last locally known state is valid after startup, reset or communication loss.

On startup or restored communication, PANEL requests a complete state synchronisation from MAIN.

Conceptual request:

```text
SYNC|201
```

MAIN responds with a complete authoritative snapshot, followed by an explicit completion marker, for example:

```text
STATE|MODE|NORMAL
STATE|FILTERPUMP|OFF
STATE|HEATPUMP|OFF
STATE|COLLECTOR|CLOSED
STATE|SOURCEPUMP|OFF
STATE|PROGRAM|NONE
SYNC_DONE|201
```

Normal LED rendering resumes only after a valid synchronisation has completed.

## 14. Communication loss

Loss of PANEL communication must not stop MAIN from safely controlling the pool system. MAIN continues independently.

PANEL must not continue displaying stale operational state indefinitely as if it were current. The exact timeout and visual communication-loss indication will be defined during implementation.

After communication is restored, a complete state synchronisation is required.

## 15. Duplicate commands and retries

Command IDs exist so retries can be handled safely.

If PANEL retransmits a command because an ACK/REJECT was not received, MAIN must avoid executing the same command twice merely because the same command ID was received again.

The exact retry timeout, retry count and duplicate-ID retention window will be determined during transport testing.

## 16. Protocol versioning

The implemented protocol must expose a protocol version before operational deployment so incompatible MAIN/PANEL firmware can be detected.

Initial target:

```text
PROTOCOL_VERSION = 1
```

The exact startup/version negotiation message will be defined together with the transport implementation.

## 17. Deferred implementation details

The following are intentionally not fixed until the MAX3485 modules are available for bench testing:

- UART baud rate
- UART framing details
- RS485 termination and bias arrangement
- transmit/receive turnaround timing
- frame timeout
- maximum frame length
- checksum/CRC requirement
- retry timeout and retry count
- communication-loss timeout
- final startup/version handshake

These details must be measured/tested on the actual MAIN <-> PANEL hardware before the protocol is promoted from design baseline to implemented protocol.
