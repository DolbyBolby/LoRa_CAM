import serial
import time

COMMAND = {
    "voltage" : 1,
    "current" : 2,
    "other"   : 3,
}


def getData(message: str, port: str = "COM5", baudrate: int = 9600) -> None:
   print("getData")

def sendData(data: bytes, port: str = "COM5", baudrate: int = 9600) -> None:
    
    try:
        with serial.Serial(port=port, baudrate=baudrate, dsrdtr=False, rtscts=False) as ser:
            
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
                    data = ser.read(ser.in_waiting)
                    response += data.decode('utf-8', errors='ignore')

            if response: 
                print(f"Réponse reçue: {response.strip()}")
            else:
                print(f"Pas de réponse")

    except serial.SerialException as e:
        print(f"Serial error: {e}")
    except Exception as e:
        print(f"Error: {e}")

def encode_command(cmd : str, value : float)->bytes:
    if cmd not in COMMAND:
        raise ValueError(f"Commande inconnue: {cmd}")
    
    value = float2int(value)
    if not 0 <= value <= 255:
        raise ValueError("La valeur doit être entre 0 et 255 pour tenir dans un uint8_t")

    cmd_id = COMMAND[cmd]

    data = bytes([cmd_id, value])
    return data

def float2int(value:float) ->int:
    return int(round(value*10))