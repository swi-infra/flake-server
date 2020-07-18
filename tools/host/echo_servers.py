from socket import socket, AF_INET, SOCK_DGRAM, SOCK_STREAM
import flog
import _thread
from config_handler import ServerConfig

TIMEOUT = 120


def tcp_handle(Client_SOCK, address, buffer):
    """Echo data over TCP socket."""
    flog.info("Launch TCP Handler.")
    while True:
        Client_SOCK.settimeout(TIMEOUT)
        data = Client_SOCK.recv(buffer)
        if data:
            Client_SOCK.send(data)
        if not data:
            Client_SOCK.close()
            break
    flog.info("End TCP Handler")


class EchoServer:
    """TCP server class."""

    def __init__(self, config):
        """Initialize echo servers."""
        self.config = config
        self.port = int(self.config["tcp_udp"]["port"])
        self.buffer = int(self.config["tcp_udp"]["buffer"])
        self.local_ip = "0.0.0.0"
        self.tcp_server = socket(AF_INET, SOCK_STREAM)
        self.udp_server = socket(AF_INET, SOCK_DGRAM)

    def udp_handle(self):
        """Echo data over UDP socket."""
        flog.info("Launch UDP Handler.")
        while True:
            data, addr = self.udp_server.recvfrom(self.buffer)
            if data:
                flog.debug("Received UDP: {}".format(data))
                self.udp_server.sendto(data, addr)
            if not data:
                self.udp_server.close()

    def run(self):
        """Run Echo servers."""

        flog.debug("Starting echo server on {}".format(self.port))
        self.tcp_server.bind((self.local_ip, self.port))
        self.udp_server.bind((self.local_ip, self.port))
        self.tcp_server.listen(5)

        # listen for UDP
        _thread.start_new_thread(self.udp_handle, ())

        # listen for TCP
        while True:
            Client_SOCK, addr = self.tcp_server.accept()
            _thread.start_new_thread(tcp_handle, (Client_SOCK, addr, self.buffer))


def run_echo_server():
    """Run echo servers."""
    flog.info("Starting TCP/UDP Echo server")
    config = ServerConfig()
    echo_servers = EchoServer(config)
    echo_servers.run()


if __name__ == "__main__":
    run_echo_server()
