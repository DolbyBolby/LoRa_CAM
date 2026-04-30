import typer
import serial
from serial_comm import sendData,getData

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
             for i in range(1,21,1):
                sendData(ser,message)
                message = ""

    except serial.SerialException as e:
        print(f"Serial error: {e}")
    except Exception as e:
        print(f"Error: {e}")
   

if __name__ == "__main__":
    app()