"""TCP / UDP echo server."""
import _thread
import multiprocessing
import os
import select
import signal
import socket
import struct
import time
import flog
from config_handler import ServerConfig


max_buffer = 65535


def tcp_handle(client_sock, killable=False):
    """Echo data over TCP socket."""
    flog.info("Launch TCP Handler.")
    while True:
        try:
            data = client_sock.recv(max_buffer)
            try:
                data_str = data.decode("utf-8")
            except Exception:
                pass
            if killable and data_str:
                if "kill" in data_str:
                    flog.debug("Killing Socket...")
                    pid = os.getpid()
                    os.kill(pid, signal.SIGKILL)
                if "stop" in data_str:
                    flog.debug("Stopping Socket...")
                    client_sock.close()
                    break
            if data:
                flog.debug("Received TCP data: %s" % data)
                client_sock.send(data)
            else:
                client_sock.close()
                break
        except Exception as ex:
            flog.warning("TCP Handler Exception: {}".format(ex))
            client_sock.close()
            break
    flog.info("End TCP Handler")


def tcp_poll_handle(client_sock):
    """Handle TCP polling client needed for killable server."""
    while True:
        try:
            data = client_sock.recv(max_buffer)
            if data:
                client_sock.send(data)
            else:
                client_sock.close()
                break
        except Exception:
            client_sock.close()
            break


class EchoServer:
    """TCP server class."""

    def __init__(self, config):
        """Initialize echo servers."""
        self.config = config
        self.port = int(self.config["tcp_udp"]["port"])
        self.kill_port = int(self.config["tcp_kill_server"]["port"])
        self.polling_port = int(self.config["tcp_kill_server"]["polling_port"])
        self.timeout = int(self.config["tcp_udp"]["timeout"])
        self.local_ip = "0.0.0.0"
        self.tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.udp_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.tcp_kill_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_local_poll_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def udp_handle(self):
        """Echo data over UDP socket."""
        flog.info("Launch UDP Handler.")
        while True:
            data, addr = self.udp_server.recvfrom(max_buffer)
            if data:
                if data == b"0 byte test":
                    flog.debug("Received 0 byte test")
                    self.udp_server.sendto(b"", addr)
                else:
                    flog.debug("Received UDP data: %s" % data)
                    self.udp_server.sendto(data, addr)
            if not data:
                self.udp_server.close()

    def run(self):
        """Run Echo servers."""
        flog.debug("Starting echo server on {}".format(self.port))
        flog.debug("Starting tcp kill server on {}".format(self.kill_port))
        self.tcp_server.bind((self.local_ip, self.port))
        self.tcp_kill_server.bind((self.local_ip, self.kill_port))
        self.tcp_local_poll_server.bind((self.local_ip, self.polling_port))
        self.udp_server.bind((self.local_ip, self.port))
        self.tcp_server.listen(5)
        self.tcp_kill_server.listen(5)
        self.tcp_local_poll_server.listen(5)
        l_onoff = 1
        l_linger = 0
        self.tcp_kill_server.setsockopt(
            socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", l_onoff, l_linger)
        )

        # listen for UDP
        _thread.start_new_thread(self.udp_handle, ())

        # listen for TCP
        while True:
            sockets, _, _ = select.select(
                (self.tcp_server, self.tcp_kill_server, self.tcp_local_poll_server),
                (),
                (),
                1,
            )
            for sock in sockets:
                client_sock, _ = sock.accept()
                client_sock.settimeout(self.timeout)
                if sock == self.tcp_server:
                    _thread.start_new_thread(tcp_handle, (client_sock, False))
                elif sock == self.tcp_kill_server:
                    x = multiprocessing.Process(
                        target=tcp_handle, args=(client_sock, True)
                    )
                    x.start()
                else:
                    _thread.start_new_thread(tcp_poll_handle, (client_sock,))
            else:
                time.sleep(1)
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as poll_socket:
                    poll_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                    poll_socket.connect_ex((self.local_ip, self.polling_port))


def run_echo_server():
    """Run echo servers."""
    flog.info("Starting TCP/UDP Echo server")
    config = ServerConfig()
    echo_servers = EchoServer(config)
    echo_servers.run()


if __name__ == "__main__":
    run_echo_server()
