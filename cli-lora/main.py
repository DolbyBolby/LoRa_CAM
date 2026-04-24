import typer
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

if __name__ == "__main__":
    app()