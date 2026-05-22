# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **LoRa wireless communication project** for ESP32 microcontrollers with SX1280 radio modules. The repository contains:

1. **ESP32_DevKitC_V4_test** - Main dual-role firmware supporting both TX (transmitter) and RX (receiver)
2. **receive_blocking** - Simplified RX implementation using interrupt-driven FSM
3. **transmitt_blocking** - Simplified TX implementation using interrupt-driven FSM
4. **cli-lora** - Python CLI tool for serial communication and data logging

All embedded code is written in C++ using the RadioLib library for LoRa abstraction.

## Architecture

### Firmware Architecture (ESP32_DevKitC_V4_test)

The main firmware follows a **header/implementation pattern** with role-based compilation:

- **config.h** - Central configuration hub containing:
  - SX1280 GPIO pin mappings (SPI: SCK/MISO/MOSI, radio-specific: NSS/DIO1/RST/BUSY)
  - LoRa radio parameters (frequency 2450 MHz, bandwidth, spreading factor, coding rate, power, preamble, CRC, sync word)
  - Serial baud rate (115200), TX interval (2000ms), RX timeout, TX message template
  - Logging macros (LOG, LOG_INFO, LOG_ERROR, LOG_DEBUG)
  - Role selection via build flags (ROLE_TX or ROLE_RX) - if unset, defaults to TX

- **sx1280_link.h/cpp** - Radio control layer:
  - SPI initialization with custom pins (VSPI peripheral)
  - SX1280 radio initialization and configuration
  - Two operating modes: `runTx()` (periodic transmission every TX_INTERVAL_MS) and `runRx()` (continuous listening with RSSI/SNR/frequency error reporting)
  - Role switching via `setRole()` enum (ROLE_TRANSMITTER=0, ROLE_RECEIVER=1)
  - State tracking: `radio_initialized`, `current_role`, `receiving` flags, `last_tx_time` for interval management

- **main.cpp** - Minimal ~60-line entry point:
  - `setup()` initializes serial (115200 baud) and calls `initRadio()`
  - `loop()` dispatches to either `runTx()` or `runRx()` based on `getCurrentRole()`
  - Role determined at compile-time via build flags in platformio.ini

### Simplified Implementations

**receive_blocking/src/main.cpp** - Interrupt-driven RX-only FSM with 3 states:
- RX_NODE → WAIT_MSG → (loop) on message receipt, calculate RSSI/SNR/frequency error

**transmitt_blocking/src/main.cpp** - Interactive TX-RX FSM with serial input:
- WAIT_SERIAL (polls Serial.available) → TX_NODE → RX_NODE → WAIT_ACK (200ms timeout) → back to WAIT_SERIAL
- Useful for ping-pong or echo testing

### Python CLI Tool (cli-lora)

**main.py** - Entry point using Typer framework with commands:
- `get` - Receive message (not implemented)
- `send` - Send single message (via serial_comm.sendData)
- `block_send` - Send message 5 times in a loop
- `log_data` - Capture N packets and save RSSI/SNR/frequency error to CSV

**serial_comm.py** - Serial communication helper:
- `sendData(ser, message)` - Write to serial with 500ms delay, read response if available

**data_logger.py** - CSV logging utility:
- `capture_and_save_data()` - Reads serial lines, parses RSSI/SNR/frequency error, saves to CSV after N complete packets

## Build & Upload Commands

All embedded projects use **PlatformIO**. Board: `esp32dev`, Framework: `arduino`, Platform: `espressif32`, Baud: `115200`.

### ESP32_DevKitC_V4_test (Main Project)

**Compile for TX (transmitter on COM5):**
```bash
pio run -e tx --target upload
```

**Compile for RX (receiver on COM3):**
```bash
pio run -e rx --target upload
```

**Compile with default TX role:**
```bash
pio run -e esp32dev --target upload
```

**Monitor serial output (115200 baud):**
```bash
pio device monitor -e tx      # Monitor TX environment
pio device monitor -p COM5 -b 115200  # Direct port monitoring
```

### receive_blocking & transmitt_blocking

Both use simpler platformio.ini with single env:esp32dev:
```bash
cd receive_blocking
pio run --target upload

cd ../transmitt_blocking
pio run --target upload
```

Monitor with `pio device monitor` at default 9600 baud (note: different from main project's 115200).

### Python CLI Tool

**Install dependencies:**
```bash
cd cli-lora
pip install typer pyserial
```

**Send a message:**
```bash
python main.py send "Hello LoRa" --port COM5 --baudrate 9600
python main.py send "Hello LoRa" --port COM4 --baudrate 9600
```

**Capture data to CSV:**
```bash
python main.py log-data 10 --port COM5 --output results.csv
```

**Send message repeatedly (5x):**
```bash
python main.py block-send "Test message" --port COM5
```

## Key Configuration Points

### Radio Parameters (config.h)

- **LORA_FREQUENCY_MHZ** (2450.0) - SX1280 operates at 2.4 GHz only
- **LORA_BANDWIDTH** (406.25 kHz) - SX1280 supports 406.25, 812.5, 1625 kHz
- **LORA_SPREADING_FACTOR** (9) - SF 5-12; higher = more range, slower
- **LORA_CODING_RATE** (5) - CR 5-8 (maps to 4/5 through 4/8)
- **LORA_TX_POWER** (10 dBm) - Max +12 dBm for SX1280
- **LORA_PREAMBLE_LENGTH** (8 symbols)
- **LORA_SYNC_WORD** (0x12)

**Critical:** Both TX and RX must use **identical radio parameters** to communicate. TX_MESSAGE can differ.

### Pin Mappings (config.h)

For ESP32 DevKit C V4 (customizable for other boards):

| Function | GPIO |
|----------|------|
| SX1280 NSS (CS) | 25 |
| SX1280 DIO1 (IRQ) | 14 |
| SX1280 RST | 2 |
| SX1280 BUSY | 13 |
| SPI SCK | 18 |
| SPI MISO | 19 |
| SPI MOSI | 23 |

### Serial Ports (platformio.ini)

- **ESP32_DevKitC_V4_test [env:tx]:** COM5
- **ESP32_DevKitC_V4_test [env:rx]:** COM3
- **receive_blocking:** COM4
- **transmitt_blocking:** COM5

Update as needed for your hardware.

## Expected Behavior

### TX Operation

- Sends configured message every 2 seconds (TX_INTERVAL_MS)
- Serial log: `[TX] Envoi du message: "..."` followed by `[INFO] TX OK - Message envoyé avec succès`
- Briefly enters standby between transmissions

### RX Operation

- Continuously listens for incoming LoRa packets
- On reception: logs message, RSSI (dBm), SNR (dB), and frequency error (Hz)
- Example output: `[RX] Message reçu ('Hello LoRa SX1280!') Longueur: 17 bytes | RSSI: -75.50 dBm | SNR: 9.25 dB`
- Restarts listening after each packet

### Simplified FSM Implementations

- **receive_blocking:** Waits for DIO1 interrupt, reads data, restarts receive
- **transmitt_blocking:** Accepts serial input, transmits, waits 200ms for echo, returns to input (ping-pong)

## Testing & Debugging

### Hardware Verification

- **SX1280 Not Detected?** Check pin definitions in config.h, verify SPI wiring (SCK=18, MISO=19, MOSI=23), ensure 3.3V power
- **TX Fails?** Verify `[INFO] TX OK` in logs; error codes are RadioLib error codes (negative integers)
- **RX Receives Nothing?** Confirm TX is transmitting, check distance (< 10m initially), verify both devices use **exact same radio parameters**, increase RX_TIMEOUT_MS if needed
- **Port Not Found?** Check Device Manager (Windows) or `ls /dev/tty*` (Linux/Mac); update platformio.ini with correct upload_port/monitor_port

### Logs Macros

- `LOG(fmt, ...)` - General messages (requires LOG_ENABLED=true)
- `LOG_INFO(fmt, ...)` - Informational
- `LOG_ERROR(fmt, ...)` - Error conditions
- `LOG_DEBUG(fmt, ...)` - Debug output (requires DEBUG_ENABLED=true)

Both toggles in config.h; when disabled, macros compile to no-ops.

## File Structure Reference

```
.
├── ESP32_DevKitC_V4_test/          # Main dual-role firmware
│   ├── include/
│   │   ├── config.h                # All configurable parameters
│   │   └── sx1280_link.h           # Radio interface declarations
│   ├── src/
│   │   ├── main.cpp                # Minimal setup/loop
│   │   └── sx1280_link.cpp         # Radio control implementation
│   ├── test/
│   │   └── test_board_ESP32_DevKit.cpp  # Unit test template
│   ├── platformio.ini              # [env:tx], [env:rx], [env:esp32dev]
│   ├── README.md                   # (Binary/unreadable)
│   └── USAGE.md                    # Detailed user guide
│
├── receive_blocking/               # RX-only interrupt FSM
│   ├── src/main.cpp
│   └── platformio.ini
│
├── transmitt_blocking/             # TX-RX ping-pong FSM
│   ├── src/main.cpp
│   └── platformio.ini
│
├── cli-lora/                       # Python serial CLI
│   ├── main.py                     # Typer CLI entry
│   ├── serial_comm.py              # Serial send/receive
│   ├── data_logger.py              # CSV capture utility
│   └── data_log.csv                # Example output
│
├── .gitignore                      # Excludes .pio, build artifacts
└── CLAUDE.md                       # This file
```

## Dependencies

**Embedded:**
- RadioLib 7.6.0+ (SX1280 LoRa driver) - auto-fetched by PlatformIO
- Arduino framework (implicit with esp32dev board definition)

**Python:**
- Typer (CLI framework)
- pyserial (serial communication)

## Notes

- French comments throughout code (`Initialisation`, `Transmission`, `Réception`) - preserve as-is or translate carefully
- All embedded code compiles to single binary; role determined at build-time or via runtime calls to `setRole()`
- RadioLib abstracts SX1280 complexity; consult RadioLib docs for error codes or advanced radio control
- No unit tests implemented; test/README.md is boilerplate
- Python CLI is minimal; suitable for serial debugging and data collection but not production use