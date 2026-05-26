import typer
from serial_comm import sendData, getData, encode_command

app = typer.Typer()


@app.command()
def get(varname: str, port: str = "COM5", baudrate: int = 9600) -> None:
    """Read a stored variable from the RX node."""
    getData(varname, port, baudrate)

@app.command()
def send(command: str, value: float, port: str = "COM5", baudrate: int = 9600) -> None:
    """Send a command and value to the RX node."""
    opCode = encode_command(command, value)
    sendData(opCode, port, baudrate)

if __name__ == "__main__":
    app()
