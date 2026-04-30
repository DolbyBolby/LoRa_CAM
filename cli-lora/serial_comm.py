import serial
import time
import csv
from datetime import datetime


def getData(message: str, port: str = "COM5", baudrate: int = 9600) -> None:
   print("getData")

def sendData(ser: serial.Serial, message: str) -> None:
    resp = ""; 
    
    if ser.in_waiting > 0:
        cln = ser.read(ser.in_waiting)
        resp += cln.decode('utf-8', errors='ignore')
        print(f"[DEBUG] Buffer nettoyé {resp}")

    bytes_sent = ser.write((message + "\n").encode('utf-8'))
    ser.flush()
    print(f"Message sent: {message} ({bytes_sent} bytes)")
    
    time.sleep(0.5)

    response = ""
    if ser.in_waiting > 0:
            data = ser.read(ser.in_waiting)
            #print(f"[DEBUG] Données brutes: {data}")
            response += data.decode('utf-8', errors='ignore')

    if response: 
        print(f"Réponse reçue: {response.strip()}")
    else:
        print(f"Pas de réponse")

