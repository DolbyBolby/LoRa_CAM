import typer
import serial
from serial_comm import sendData,getData
from data_logger import capture_and_save_data, sweep_capture_and_save_data

app = typer.Typer()


@app.command()
def get(message: str, port: str = "COM5", baudrate: int = 9600) -> None:
    """Send a message via serial port."""
    getData(message, port, baudrate)

@app.command()
def send(message: str, port: str = "COM5", baudrate: int = 9600) -> None:
    """Send a message via serial port."""
    ser = serial.Serial(port, baudrate)
    sendData(ser,message)
    #ser.close()

@app.command()
def block_send(message: str, port: str = "COM5", baudrate: int = 9600) -> None:
    try:
        with serial.Serial(port=port, baudrate=baudrate, dsrdtr=False, rtscts=False) as ser:
             for i in range(1,6,1):
                sendData(ser,message)
                message = ""

    except serial.SerialException as e:
        print(f"Serial error: {e}")
    except Exception as e:
        print(f"Error: {e}")
   
@app.command()
def log_data(
    num_packets: int,
    port: str = "COM5",
    baudrate: int = 9600,
    output: str = "data_log.csv",
) -> None:
    """Capture NUM_PACKETS paquets LoRa et sauvegarde RSSI/SNR/Frequency Error.

    Le fichier de sortie peut être .csv ou .xlsx (Excel).

    Exemples :
        python main.py log-data 50 --port COM4
        python main.py log-data 100 --port COM4 --output resultats.xlsx
    """
    capture_and_save_data(num_packets=num_packets, port=port, baudrate=baudrate, output_file=output)

@app.command()
def sweep_log(
    port: str = "COM4",
    baudrate: int = 9600,
    output: str = "sweep_results.xlsx",
    verbose: bool = typer.Option(False, "--verbose", "-v",
                                 help="Affiche toutes les lignes brutes reçues (diagnostic)"),
) -> None:
    """Lance le logger pour le sweep complet SF/BW/CR (128 compositions).

    Le firmware transmitt_blocking doit tourner sur l'autre ESP32.
    Le firmware receive_blocking doit tourner sur l'ESP32 connecté à PORT.

    Exemples :
        python main.py sweep-log --port COM4
        python main.py sweep-log --port COM4 --verbose        (diagnostic)
        python main.py sweep-log --port COM4 --output resultats_sweep.xlsx
    """
    sweep_capture_and_save_data(port=port, baudrate=baudrate,
                                output_file=output, verbose=verbose)

if __name__ == "__main__":
    app()