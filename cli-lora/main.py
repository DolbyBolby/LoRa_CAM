import typer
from serial_comm import send_string

app = typer.Typer()


@app.command()
def send(message: str, port: str = "COM1", baudrate: int = 19200) -> None:
    """Send a message via serial port."""
    send_string(message, port, baudrate)


if __name__ == "__main__":
    app()