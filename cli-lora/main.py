import typer
from serial_comm import send_string, send_and_receive

app = typer.Typer()


@app.command()
def basic_send(message: str, port: str = "COM5", baudrate: int = 9600) -> None:
    """Send a message via serial port."""
    send_string(message, port, baudrate)

@app.command()
def send(message: str, port: str = "COM5", baudrate: int = 9600) -> None:
    """Send a message via serial port."""
    send_and_receive(message, port, baudrate)

if __name__ == "__main__":
    app()