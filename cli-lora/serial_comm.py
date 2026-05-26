import serial
import time

COMMAND = {
    "voltage"     : 1,
    "current"     : 2,
    "temperature" : 3,
    "status"      : 4,
}

# NOTE: 0xFF is reserved as the GET flag and cannot be used as a SEND value.
#       Valid encoded values are 0–254 (display range 0.0–25.4 with ×10 encoding).
GET_FLAG = 0xFF

OPCODE_TO_VAR = {v: k for k, v in COMMAND.items()}


def getData(varname: str, port: str = "COM5", baudrate: int = 9600) -> None:
    if varname not in COMMAND:
        print(f"Unknown variable: '{varname}'. Valid names: {', '.join(COMMAND)}")
        return

    opcode = COMMAND[varname]
    payload = bytes([opcode, GET_FLAG])

    try:
        with serial.Serial(port=port, baudrate=baudrate, dsrdtr=False, rtscts=False) as ser:
            if ser.in_waiting > 0:
                ser.read(ser.in_waiting)

            ser.write(payload)
            ser.flush()

            deadline = time.time() + 2.0
            while time.time() < deadline:
                if ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line.startswith("GET:"):
                        parts = line.split(":")
                        if len(parts) == 3:
                            raw_val = int(parts[2])
                            display = raw_val / 10.0
                            print(f"GET {varname}: {display}")
                            return
                time.sleep(0.05)

            print(f"[TIMEOUT] No GET response received for '{varname}'")

    except serial.SerialException as e:
        print(f"Serial error: {e}")
    except Exception as e:
        print(f"Error: {e}")


def sendData(data: bytes, port: str = "COM5", baudrate: int = 9600) -> None:
    try:
        with serial.Serial(port=port, baudrate=baudrate, dsrdtr=False, rtscts=False) as ser:
            resp = ""
            if ser.in_waiting > 0:
                cln = ser.read(ser.in_waiting)
                resp += cln.decode('utf-8', errors='ignore')
                print(f"[DEBUG] Buffer nettoyé {resp}")

            bytes_sent = ser.write(data)
            ser.flush()
            print(f"Message sent: cmd = {data[0]} value = {data[1]} ({bytes_sent} bytes)")

            time.sleep(0.5)

            response = ""
            if ser.in_waiting > 0:
                chunk = ser.read(ser.in_waiting)
                response += chunk.decode('utf-8', errors='ignore')

            if response:
                print(f"Réponse reçue: {response.strip()}")
            else:
                print(f"Pas de réponse")

    except serial.SerialException as e:
        print(f"Serial error: {e}")
    except Exception as e:
        print(f"Error: {e}")


def encode_command(cmd: str, value: float) -> bytes:
    if cmd not in COMMAND:
        raise ValueError(f"Commande inconnue: {cmd}")

    encoded = float2int(value)
    if not 0 <= encoded <= 254:
        raise ValueError(
            f"Encoded value {encoded} out of range. "
            "Valid display range is 0.0–25.4 (×10 encoding, 0xFF reserved as GET flag)."
        )

    cmd_id = COMMAND[cmd]
    return bytes([cmd_id, encoded])


def float2int(value: float) -> int:
    return int(round(value * 10))
