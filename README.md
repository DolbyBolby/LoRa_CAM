# LoRa 2.4 GHz Bidirectional Link — SX1280 / ESP32-WROOM-32

## Project Overview

This repository contains the firmware and software developed as part of a semester project at the **Center for Artificial Muscles (CAM) / LAI laboratory, EPFL**.

The CAM laboratory is developing an innovative cardiac assist device consisting of a soft artificial muscle wrapped around the aorta. The actuator — a Dielectric Elastomer Actuator (DEA) — is implanted near the aortic valve and contracts to supplement the heart's pumping action. Unlike conventional cardiac technologies, this device does not interface directly with the heart, making it significantly less invasive. To ensure correct operation of the implanted actuator, the electrical signals applied to it (voltage, current) must be monitored in real time from outside the body.

This project establishes a **bidirectional wireless LoRa link at 2.4 GHz** between an external PC terminal and the remote embedded node, enabling real-time monitoring and command of the actuator parameters. The targeted hardware is two **Ebyte E28-2G4M12XX** modules integrating the **Semtech SX1280** chip, driven by **ESP32-WROOM-32** microcontrollers over SPI. The radio link features a full acknowledge mechanism (ACK/NACK) to guarantee reliable delivery of each command.

The complete system comprises:
- A PC terminal (Python CLI) as the user interface
- Two **ESP32-WROOM-32** modules as UART ↔ SPI bridges
- Two **SX1280** radio modules driven via SPI
- A **LoRa 2.4 GHz** bidirectional radio link

---

## Repository Structure

```
.
├── master_side/          # Firmware for the PC-side ESP32 (COM5)
│   ├── src/main.cpp      # FSM: UART receive → LoRa TX → wait ACK
│   └── platformio.ini    # PlatformIO config, upload_port = COM5
│
├── slave_side/           # Firmware for the remote-node ESP32 (COM4)
│   ├── src/main.cpp      # FSM: LoRa receive → echo → wait confirm
│   └── platformio.ini    # PlatformIO config, upload_port = COM4
│
└── cli-lora/             # Python CLI
    ├── main.py           # Typer entry point — exposes `send` and `get` commands
    └── serial_comm.py    # Binary encoding and serial I/O logic
```

---

## Requirements

### Python (CLI)

Python 3.9 or later is required.

```bash
pip install typer pyserial
```

### Firmware

- [PlatformIO](https://platformio.org/) (CLI or IDE extension)
- [RadioLib](https://github.com/jgromes/RadioLib) `^7.6.0` — declared in each `platformio.ini`, installed automatically by PlatformIO

---

## Flashing the Firmware

Each node is a separate PlatformIO project with its own `platformio.ini`. Flash them independently.

### Master side (PC-side ESP32 — COM5)

```bash
cd master_side

# Build
pio run

# Upload
pio run --target upload

# Monitor serial output (9600 baud)
pio device monitor -p COM5 -b 9600
```

### Slave side (remote-node ESP32 — COM4)

```bash
cd slave_side

# Build
pio run

# Upload
pio run --target upload

# Monitor serial output (9600 baud)
pio device monitor -p COM4 -b 9600
```

> **Note:** Update `upload_port` and `monitor_port` in `platformio.ini` if your COM port assignment differs.

---

## Using the Python CLI

The CLI is located in `cli-lora/` and exposes two sub-commands. The default port is `COM5` and the default baudrate is `9600`.

### `send` — Write a value to the remote node

```bash
python main.py send <command> <value> [--port COMx] [--baudrate 9600]
```

Available command names: `voltage`, `current`, `temperature`, `status`

Values are input as floats (one decimal place). Internally they are encoded as integers ×10 (e.g. `5.0` → byte `50`). Valid input range is `0.0` to `25.4`.

```bash
# Send 5.0 V to the remote node
python main.py send voltage 5.0 --port COM5

# Send 1.2 A
python main.py send current 1.2 --port COM5
```

### `get` — Read a stored variable from the remote node

```bash
python main.py get <varname> [--port COMx] [--baudrate 9600]
```

```bash
# Read the current voltage stored on the remote node
python main.py get voltage --port COM5

# Read temperature
python main.py get temperature --port COM5
```

The CLI waits up to 2 seconds for a response. On success it prints `GET <varname>: <value>`.

---

## Communication Protocol

Every transaction uses a **2-byte binary frame** sent over UART from the CLI to the master-side ESP32, which relays it over LoRa.

```
┌─────────────────┬──────────────────────────────────────────────────────┐
│  Byte 0 (cmd)   │  Byte 1 (value)                                      │
│  uint8          │  uint8                                                │
├─────────────────┼──────────────────────────────────────────────────────┤
│  1 = voltage    │  0x00–0xFE → SEND: encoded value (float × 10)        │
│  2 = current    │  0xFF      → GET:  request to read the stored value   │
│  3 = temperature│                                                       │
│  4 = status     │                                                       │
└─────────────────┴──────────────────────────────────────────────────────┘
```

### ACK mechanism

After the slave node echoes the 2-byte frame back over LoRa, the master validates the echo and sends a 1-byte confirmation:

| Byte | Meaning |
|------|---------|
| `0xAA` | Echo matches — transaction confirmed |
| `0xFF` | Echo mismatch — transaction rejected, master retransmits |

If no echo is received within **200 ms**, the master retransmits automatically. The slave waits up to **300 ms** for the confirmation before resetting to idle.

### Master-side FSM

```
WAIT_SERIAL (≥2 bytes) → TX_NODE → RX_NODE → WAIT_ACK (200 ms) → SEND_CONFIRM → WAIT_SERIAL
                                                        │                   │
                                               timeout / bad read       mismatch
                                                        └───────────────────┘
                                                              TX_NODE (retry)
```

### Slave-side FSM

```
WAIT_MSG → TX_NODE (echo 2 bytes) → RX_NODE → WAIT_CONFIRM (300 ms) → WAIT_MSG
```

The slave maintains an in-RAM variable store. On a **SEND** command it persists the received value; on a **GET** request it substitutes the `0xFF` placeholder with the stored value before echoing.

---

## Credits

| Role | Name |
|------|------|
| Author | Eliott Loeffel |
| Supervisor | Marc-Olivier Arrigo |
| Professor | Yves Perriard |
| Laboratory | CAM / LAI — EPFL |
