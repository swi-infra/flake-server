"""TCP client tool."""
import select
from socket import socket, AF_INET, SOCK_STREAM
import flog


MAX_BUFFER = 65535
DEFAULT_TIMEOUT = 120


class EchoClient:
    """TCP client class."""

    def __init__(
        self,
        address,
        port,
        message="Hello from Flake Client!",
        echo=False,
        timeout=DEFAULT_TIMEOUT,
    ):
        """Initialize TCP server."""
        self.address = address
        self.port = port
        self.message = message
        self.echo = echo
        self.timeout = timeout
        self.tcp_client = socket(AF_INET, SOCK_STREAM)
        self.tcp_client.settimeout(self.timeout)

    def send(self, data):
        """Send encoded data to server."""
        try:
            flog.info("Sending data of length: %d" % len(data))
            self.tcp_client.send(data)
        except (BlockingIOError, ConnectionResetError, socket.timeout) as e:
            flog.debug(e)

    def receive(self):
        """Receive encoded data from server."""
        data = b""
        wait_time = 5
        got_data = False
        for _ in range(0, self.timeout, wait_time):
            sockets, _, _ = select.select((self.tcp_client,), (), (), wait_time)
            for sock in sockets:
                data += sock.recv(MAX_BUFFER)
                got_data = data != b""
                flog.debug("Data part received length: %d" % len(data))
                break
            else:
                if got_data:
                    flog.debug("Data parts complete")
                    break
                # time.sleep(1)
        if not got_data:
            return None
        flog.info("Received message of length: %s bytes" % len(data))
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

    def run(self):
        """Run TCP client."""
        flog.info("Connecting to tcp server at {}:{}".format(self.address, self.port))
        self.tcp_client.connect((self.address, self.port))

        while True:
            try:
                if self.echo:
                    data = self.receive()
                    if not data or self.check_message(data) == "close":
                        self.tcp_client.close()
                        break
                    self.send(data)
                else:
                    self.send(self.message.encode())
                    data = self.receive()
                    if not data or self.check_message(data) == "close":
                        self.tcp_client.close()
                        break
            except Exception as ex:
                flog.warning("TCP Client Exception: {}".format(ex))
                self.tcp_client.close()
                break
        flog.info("End TCP Client")
