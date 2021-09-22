#!/usr/bin/env python3
"""TCP client tool."""
import argparse
from socket import socket, AF_INET, SOCK_STREAM
import flog
from config_handler import ServerConfig


MAX_BUFFER = 65535
DEFAULT_TIMEOUT = 120


class EchoClient:
    """TCP client class."""

    def __init__(self, config, address, port, message, echo=False):
        """Initialize echo servers."""
        self.config = config
        self.address = address
        self.port = port
        self.message = message
        self.echo = echo
        try:
            self.timeout = int(self.config["tcp_udp"]["timeout"])
        except (KeyError, ValueError):
            flog.warning(
                "Could not use specified timeout, using default value: %d"
                % DEFAULT_TIMEOUT
            )
            self.timeout = DEFAULT_TIMEOUT
        self.tcp_client = socket(AF_INET, SOCK_STREAM)
        self.tcp_client.settimeout(self.timeout)

    def send(self, data):
        """Send encoded data to server."""
        try:
            self.tcp_client.sendall(data)
        except (BlockingIOError, ConnectionResetError, socket.timeout) as e:
            flog.debug(e)

    def receive(self):
        """Receive encoded data from server."""
        try:
            data = self.tcp_client.recv(MAX_BUFFER)
            flog.debug("Received message of length: %s bytes" % len(data))
            return data
        except (BlockingIOError, ConnectionResetError, socket.timeout) as e:
            flog.debug(e)
        return None

    def run(self):
        """Run TCP client."""
        flog.info("Connecting to tcp server at {}:{}".format(self.address, self.port))
        self.tcp_client.connect((self.address, self.port))

        while True:
            try:
                if self.echo:
                    data = self.receive()
                    if not data:
                        self.tcp_client.close()
                        break
                    self.send(data)
                else:
                    self.send(self.message.encode())
                    data = self.receive()
                    if not data:
                        self.tcp_client.close()
                        break
            except Exception as ex:
                flog.warning("TCP Client Exception: {}".format(ex))
                self.tcp_client.close()
                break
        flog.info("End TCP Client")


def main():
    """Run echo servers."""
    parser = argparse.ArgumentParser(description="Flake Legato TCP Client.")
    parser.add_argument(
        "-s", "--server", type=str, help="tcp server address", required=True
    )
    parser.add_argument("-p", "--port", type=int, help="tcp server port", required=True)
    parser.add_argument(
        "-m",
        "--message",
        type=str,
        help="message to send to server",
        default="Hello from Flake Client!",
    )
    parser.add_argument(
        "-e", "--echo", action="store_true", help="act as tcp echo client"
    )
    args = parser.parse_args()
    flog.info("Starting TCP client")
    config = ServerConfig()
    echo_client = EchoClient(
        config=config,
        address=args.server,
        port=args.port,
        message=args.message,
        echo=args.echo,
    )
    echo_client.run()


if __name__ == "__main__":
    main()
