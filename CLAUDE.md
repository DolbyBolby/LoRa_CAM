# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LoRa 2.4 GHz communication system for ESP32 + SX1280 radio modules, targeting a pipeline where a PC terminal sends commands over UART to an ESP32, which relays them wirelessly to a second SX1280 connected to a STM32 Nucleo board.

## Build & Upload Commands

All embedded projects use PlatformIO. Run these from each project's subdirectory.

```bash
# master_side (PC-side ESP32, COM5)
pio run --target upload                # Single env:esp32dev
pio device monitor -p COM5 -b 9600

# slave_side (Nucleo-side ESP32, COM4)
pio run --target upload                # Single env:esp32dev
pio device monitor -p COM4 -b 9600
```

```bash
# Python CLI (cli-lora/)
pip install typer pyserial openpyxl
python main.py send voltage 5 --port COM5 --baudrate 9600
python main.py get "status" --port COM5
```

## Architecture

### Project Inventory

| Directory | Purpose | Library | Baud |
|-----------|---------|---------|------|
| `master_side` | PC-side ESP32: receives serial, transmits LoRa, waits for echo | RadioLib 7.6 | 9600 |
| `slave_side` | Nucleo-side ESP32: receives LoRa, echoes back to sender | RadioLib 7.6 | 9600 |
| `cli-lora` | Python CLI to send commands over serial | pyserial/typer | — |

### Binary Wire Protocol (cli-lora ↔ master_side)

The CLI sends **exactly 2 raw bytes** over UART:

```
[cmd_byte (uint8)] [value_byte (uint8)]
```

- `cmd_byte`: from the `COMMAND` dict in `serial_comm.py` (`voltage=1`, `current=2`, `temperature=3`, `status=4`)
- `value_byte`: `int(round(float_value * 10))` — one decimal place encoded as integer (e.g., `5.0 V → 50`), or `0xFF` for a GET request

`master_side` polls `Serial.available() >= 2` before reading, so it strictly requires both bytes to arrive together. The firmware echoes the same 2 bytes back over LoRa; `slave_side` re-transmits those bytes as a LoRa packet; `master_side` waits 200 ms for the echo (WAIT_ACK state) and retransmits on timeout.

### master_side / slave_side FSMs

**master_side** (PC-side, COM5, pins `25,14,2,13`):
```
WAIT_SERIAL (≥2 bytes) → TX_NODE → RX_NODE → WAIT_ACK (200ms) → SEND_CONFIRM → WAIT_SERIAL
                                                              ↓ timeout                ↓ mismatch
                                                           TX_NODE (retry)          TX_NODE (retry)
```

**slave_side** (Nucleo-side, COM4, pins `25,27,2,13`):
```
WAIT_MSG → TX_NODE (echo 2 bytes) → RX_NODE → WAIT_CONFIRM (300ms) → WAIT_MSG
```
`slave_side` maintains an in-RAM variable store (`voltage`, `current`, `temperature`, `status`). On SEND it persists the received value; on GET it substitutes `0xFF` with the stored value before echoing.

## Key Configuration Points

**Radio Parameters** (both nodes use RadioLib SX1280 defaults via `radio.begin()` with no arguments):
- SX1280 supports only 2.4 GHz band; valid BWs: 203.125, 406.25, 812.5, 1625 kHz
- Both nodes must use identical parameters to communicate

**Serial Ports** (update in each project's `platformio.ini` as needed):
- `master_side`: COM5 (9600 baud)
- `slave_side`: COM4 (9600 baud)

## RadioLib Error Codes

Negative return values from RadioLib functions are error codes. `RADIOLIB_ERR_NONE` (0) is success. Common negative codes: `-2` (invalid frequency), `-5` (chip not found), `-706` (SPI error). Full list in RadioLib source `src/TypeDef.h`.
