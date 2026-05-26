# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LoRa 2.4 GHz communication system for ESP32 + SX1280 radio modules, targeting a pipeline where a PC terminal sends commands over UART to an ESP32, which relays them wirelessly to a second SX1280 connected to a STM32 Nucleo board.

## Build & Upload Commands

All embedded projects use PlatformIO. Run these from each project's subdirectory.

```bash
# Main dual-role firmware (ESP32_DevKitC_V4_test)
pio run -e tx --target upload          # TX role on COM5
pio run -e rx --target upload          # RX role on COM3
pio device monitor -p COM5 -b 115200   # Monitor TX

# Simplified projects (receive_blocking, transmitt_blocking)
pio run --target upload                # Single env:esp32dev
pio device monitor -p COM4 -b 9600    # These use 9600 baud, not 115200
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
| `ESP32_DevKitC_V4_test` | Main dual-role TX/RX firmware | RadioLib 7.6 | 115200 |
| `transmitt_blocking` | PC-side ESP32: receives serial, transmits LoRa, waits for echo | RadioLib 7.6 | 9600 |
| `receive_blocking` | Nucleo-side ESP32: receives LoRa, echoes back to sender | RadioLib 7.6 | 9600 |
| `lora_sand_misty_lib` | Abandoned experiment (915 MHz, sandeepmistry/LoRa library) | sandeepmistry | — |
| `test_IDF` | Empty ESP-IDF scaffold (`app_main(){}`) | ESP-IDF | — |
| `cli-lora` | Python CLI to send commands over serial | pyserial/typer | — |

### Binary Wire Protocol (cli-lora ↔ transmitt_blocking)

The CLI sends **exactly 2 raw bytes** over UART:

```
[cmd_byte (uint8)] [value_byte (uint8)]
```

- `cmd_byte`: from the `COMMAND` dict in `serial_comm.py` (`voltage=1`, `current=2`, `other=3`)
- `value_byte`: `int(round(float_value * 10))` — one decimal place encoded as integer (e.g., `5.0 V → 50`)

`transmitt_blocking` polls `Serial.available() >= 2` before reading, so it strictly requires both bytes to arrive together. The firmware echoes the same 2 bytes back over LoRa; `receive_blocking` re-transmits those bytes as a LoRa packet; `transmitt_blocking` waits 200 ms for the echo (WAIT_ACK state) and retransmits on timeout.

### transmitt_blocking / receive_blocking FSMs

**transmitt_blocking** (PC-side, COM5, hardcoded pins `25,14,2,13`):
```
WAIT_SERIAL (≥2 bytes) → TX_NODE → RX_NODE → WAIT_ACK (200ms) → WAIT_SERIAL
                                                              ↓ timeout
                                                           TX_NODE (retry)
```

**receive_blocking** (Nucleo-side, COM4, hardcoded pins `25,27,2,13`):
```
WAIT_MSG → TX_NODE (echo same 2 bytes) → RX_NODE → WAIT_MSG
```
Note: despite its name, `receive_blocking` also transmits (echo).

### Main Firmware (ESP32_DevKitC_V4_test)

Role is set at **compile time** via `-D ROLE_TX` / `-D ROLE_RX` build flags — not at runtime. All radio parameters live in `include/config.h`; both TX and RX **must use identical parameters** to communicate.

The SPI bus is instantiated explicitly as `SPIClass spi_radio(VSPI)` — relevant if porting to other ESP32 variants where VSPI/HSPI assignment differs.

### Sweep Data Logger (branch: test_rssi)

`cli-lora/data_logger.py` contains `SweepLogger`, which parses a structured serial protocol emitted by the firmware during a parameter sweep. The protocol lines are:

```
COMP_START|{comp_id}|{sf}|{bw}|{cr}
PKT_RX|{comp_id}|{seq}|{rssi}|{snr}|{freq_err}
SWEEP_DONE
```

The logger generates a 3-sheet Excel file (Raw Data, Summary, Heatmaps) with incremental saves after each composition. `Link_Margin_dB` in the Summary sheet is computed as `RSSI_Mean − (−120 dBm)` — a fixed reference, not SF/BW-dependent theoretical sensitivity.

## Key Configuration Points

**Radio Parameters** (`ESP32_DevKitC_V4_test/include/config.h`):
- Default: 2450 MHz, BW 406.25 kHz, SF 9, CR 5 (= 4/5), +10 dBm
- SX1280 supports only 2.4 GHz band; valid BWs: 203.125, 406.25, 812.5, 1625 kHz
- `transmitt_blocking` uses hardcoded `begin(2400, 406.25, 7, 5)` — not governed by config.h

**Serial Ports** (update in `platformio.ini` as needed):
- `ESP32_DevKitC_V4_test [env:tx]`: COM5, `[env:rx]`: COM3
- `transmitt_blocking`: COM5 (9600 baud)
- `receive_blocking`: COM4 (9600 baud)

## RadioLib Error Codes

Negative return values from RadioLib functions are error codes. `RADIOLIB_ERR_NONE` (0) is success. Common negative codes: `-2` (invalid frequency), `-5` (chip not found), `-706` (SPI error). Full list in RadioLib source `src/TypeDef.h`.
