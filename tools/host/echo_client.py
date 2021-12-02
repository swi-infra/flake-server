"""TCP client tool."""
import select
from socket import socket, AF_INET, SOCK_STREAM, SOCK_DGRAM
import flog


MAX_BUFFER = 65535
DEFAULT_TIMEOUT = 120


class EchoClient:
    """TCP/UDP client class."""

    def __init__(
        self,
        address,
        port,
        message="Hello from Flake Client!",
        echo=False,
        mode="tcp",
        local_port=None,
        timeout=DEFAULT_TIMEOUT,
    ):
        """Initialize TCP/UDP server."""
        self.address = address
        self.port = port
        self.message = message
        self.echo = True if echo in ["True", "true", "T", "t", "1", 1] else False
        self.mode = mode.upper()
        self.local_port = local_port
        self.timeout = timeout

    def send(self, data):
        """Send encoded data to server."""
        try:
            flog.info(f"Sending data of length: {len(data)}")
            self.client.send(data)
        except (BlockingIOError, ConnectionResetError, socket.timeout) as e:
            flog.debug(e)

    def receive(self):
        """Receive encoded data from server."""
        data = b""
        wait_time = 1
        got_data = False
        for _ in range(0, self.timeout, wait_time):
            sockets, _, _ = select.select((self.client,), (), (), wait_time)
            for sock in sockets:
                data += sock.recv(MAX_BUFFER)
                got_data = data != b""
                flog.debug(f"Data part received length: {len(data)}")
                break
            else:
                if got_data:
                    flog.debug("Data parts complete")
                    break
        if not got_data:
            return None
        flog.info(f"Received message of length: {len(data)} bytes")
        return data

    def check_message(self, message):
        "Check if message has command encoded."
        try:
            data_str = message.decode("utf-8")
            flog.debug(data_str)
            if "close" in data_str:
                flog.info("Received close command")
                return "close"
        except Exception:
            pass
        return ""

    def run_tcp(self):
        """Run TCP client."""
        self.client = socket(AF_INET, SOCK_STREAM)
        self.client.settimeout(self.timeout)
        self.client.connect((self.address, self.port))

        while True:
            try:
                if self.echo:
                    data = self.receive()
                    if not data or self.check_message(data) == "close":
                        self.client.close()
                        break
                    self.send(data)
                else:
                    self.send(self.message.encode())
                    data = self.receive()
                    if not data or self.check_message(data) == "close":
                        self.client.close()
                        break
            except Exception as ex:
                flog.warning(f"TCP Client Exception: {ex}")
                self.client.close()
                break

    def run_udp(self):
        """Run UDP client."""
        self.client = socket(AF_INET, SOCK_DGRAM)
        self.client.settimeout(self.timeout)
        data = self.message.encode()
        addr = (self.address, self.port)
        self.client.bind(("0.0.0.0", self.local_port))

        while True:
            if not self.echo:
                data = self.message.encode()
            try:
                flog.info(f"Sending data of length: {len(data)}")
                self.client.sendto(data, addr)
                data, addr = self.client.recvfrom(MAX_BUFFER)
                flog.info(f"Received message of length: {len(data)} bytes")
                if not data or self.check_message(data) == "close":
                    self.client.close()
                    break
            except Exception as ex:
                flog.warning(f"UDP Client Exception: {ex}")
                self.client.close()
                break

    def run(self):
        """Run TCP/UDP client."""
        flog.info(f"Connecting to {self.mode} server at {self.address}:{self.port}")
        flog.debug(f"Echo: {self.echo}")
        if not self.echo:
            flog.debug(f"Message Size: {len(self.message)}")
        if self.mode == "TCP":
            self.run_tcp()
        elif self.mode == "UDP":
            self.run_udp()
        else:
            flog.error(
                f"Cannot run client in mode: {self.mode}\nplease use either TCP or UDP"
            )
            return
        flog.info(f"End {self.mode} Client")
