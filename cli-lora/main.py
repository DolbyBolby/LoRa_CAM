import typer
from serial_comm import sendData,getData,encode_command

app = typer.Typer()


@app.command()
def get(message: str, port: str = "COM5", baudrate: int = 9600) -> None:
    """Send a message via serial port."""
    getData(message, port, baudrate)

@app.command()
def send(command: str, value: float, port: str = "COM5", baudrate: int = 9600) -> None:
    """Send a message via serial port."""
    opCode = encode_command(command,value)
    sendData(opCode, port, baudrate)

if __name__ == "__main__":
    app()