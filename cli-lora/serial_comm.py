import serial
import time


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

def send_and_receive(message: str, port: str = "COM5", baudrate: int = 9600, 
                     timeout: float = 1 ) -> None:
    
    in_if = 0
    out_if = 0

    try:
        message_str = str(message)
        with serial.Serial(port=port, baudrate=baudrate, 
                          timeout=timeout, 
                          bytesize=8,           
                          stopbits=1,
                          parity='N',
                          dsrdtr=False, 
                          rtscts=False) as ser:
            
            if ser.in_waiting > 0:
                cln = ser.read(ser.in_waiting)
                resp += cln.decode('utf-8', errors='ignore')
                print(f"[DEBUG] Buffer nettoyé {resp}")
            
            time.sleep(0.2)
            
            bytes_sent = ser.write((message_str + "\n").encode('utf-8'))
            ser.flush()
            print(f"Message sent: {message_str} ({bytes_sent} bytes)")
            
            time.sleep(1)
            
            response = ""
            start_time = time.time()
            # last_data_time = time.time()
            # ack = False

        
            # if ser.in_waiting > 0:
            #     data = ser.read(ser.in_waiting)
            #     response += data.decode('utf-8', errors='ignore')
            
            # while (time.time() - start_time) < (timeout):
            #     if ser.in_waiting > 0:
            #         data = ser.read(ser.in_waiting)
            #         #print(f"[DEBUG] Données brutes: {data}")
            #         response += data.decode('utf-8', errors='ignore')
            #         # last_data_time = time.time()
            #         # if response and (time.time() - last_data_time) > 0.2:
            #         #     print(f"Confirmation reçue: {response.strip()}")
            #         #     ack = True
            #         #     break
            #         in_if += 1
            #     out_if += 1
            
            if ser.in_waiting > 0:
                    data = ser.read(ser.in_waiting)
                    #print(f"[DEBUG] Données brutes: {data}")
                    response += data.decode('utf-8', errors='ignore')

            #if "[ACK]" in response and message in response:
            #    print(f"Réponse reçue: {response.strip()}")
            if response: 
                print(f"Réponse reçue: {response.strip()}   in_if : {in_if} out_if : {out_if}")
                in_if = out_if = 0
            else:
                print(f"Pas de réponse")
                in_if = out_if = 0

    except serial.SerialException as e:
        print(f"Serial error: {e}")
    except Exception as e:
        print(f"Error: {e}")