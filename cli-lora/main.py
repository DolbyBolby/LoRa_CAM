import typer
import serial
from serial_comm import sendData,getData
from data_logger import capture_and_save_data

app = typer.Typer()


@app.command()
def get(message: str, port: str = "COM5", baudrate: int = 9600) -> None:
    """Send a message via serial port."""
    getData(message, port, baudrate)

@app.command()
def send(message: str, port: str = "COM5", baudrate: int = 9600) -> None:
    """Send a message via serial port."""
    sendData(message, port, baudrate)

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
def log_data(num_packets: int, port: str = "COM5", baudrate: int = 9600, output: str = "data_log.csv") -> None:
    """Capture et sauvegarde les données en CSV.
    
    Args:
        num_packets: Nombre de paquets à capturer
        port: Port série (ex: COM4)
        baudrate: Vitesse de transmission
        output: Nom du fichier CSV de sortie
    """
    capture_and_save_data(num_packets=num_packets, port=port, baudrate=baudrate, csv_file=output)

if __name__ == "__main__":
    app()