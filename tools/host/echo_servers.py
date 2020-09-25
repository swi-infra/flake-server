"""TCP / UDP echo server."""
import _thread
from socket import socket, AF_INET, SOCK_DGRAM, SOCK_STREAM
import flog
from config_handler import ServerConfig


max_buffer = 65535


def tcp_handle(client_sock, address):
    """Echo data over TCP socket."""
    flog.info("Launch TCP Handler.")
    while True:
        try:
            data = client_sock.recv(max_buffer)
            if data:
                flog.debug("Received TCP data")
                client_sock.send(data)
            if not data:
                client_sock.close()
                break
        except ConnectionResetError:
            flog.info("TCP Client Disconnected.")
            client_sock.close()
            break
        except Exception as ex:
            flog.warning("TCP Handler Exception: {}".format(ex))
            client_sock.close()
            break
    flog.info("End TCP Handler")


class EchoServer:
    """TCP server class."""

    def __init__(self, config):
        """Initialize echo servers."""
        self.config = config
        self.port = int(self.config["tcp_udp"]["port"])
        self.timeout = int(self.config["tcp_udp"]["timeout"])
        self.local_ip = "0.0.0.0"
        self.tcp_server = socket(AF_INET, SOCK_STREAM)
        self.udp_server = socket(AF_INET, SOCK_DGRAM)

    def udp_handle(self):
        """Echo data over UDP socket."""
        flog.info("Launch UDP Handler.")
        while True:
            data, addr = self.udp_server.recvfrom(max_buffer)
            if data:
                flog.debug("Received UDP data")
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
            client_sock, addr = self.tcp_server.accept()
            client_sock.settimeout(self.timeout)
            _thread.start_new_thread(tcp_handle, (client_sock, addr))


def run_echo_server():
    """Run echo servers."""
    flog.info("Starting TCP/UDP Echo server")
    config = ServerConfig()
    echo_servers = EchoServer(config)
    echo_servers.run()


if __name__ == "__main__":
    run_echo_server()
