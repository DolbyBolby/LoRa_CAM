import serial


def send_string(message: str, port: str = "COM5", baudrate: int = 9600) -> None:
    """Send a string via serial connection."""
    try:
        with serial.Serial(port=port, baudrate=baudrate, timeout=1, dsrdtr=False) as ser:
            ser.write(message.encode())
            print(f"✓ Message sent: {message}")
    except serial.SerialException as e:
        print(f"✗ Serial error: {e}")
    except Exception as e:
        print(f"✗ Error: {e}")