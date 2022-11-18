import os
import time
from socket import socket, AF_INET, SOCK_DGRAM
import threading
import flog
from config_handler import ConfigHandler
from dtls import wrapper as dtls_wrapper
from dtls import do_patch

do_patch()

CONFIG = "$FLAKE_TOOLS/host/config/data_files.json"


class UdpServer:
    """UDP server class."""

    def __init__(self, config, secure=False, echo=False):
        """Initialize udp server."""
        self.config = config
        self.buffer = int(self.config.server["udp"]["buffer"])
        self.root = os.path.expandvars("$FLAKE_SERVER/public")
        self.fullchain = self.config.server["dtls"]["fullchain"]
        self.privkey = self.config.server["dtls"]["privkey"]
        self.secure = secure
        self.echo = echo
        if self.secure is False:
            self.port = int(self.config.server["udp"]["port"])
            self.name = "UDP SERVER"
        else:
            if self.echo is False:
                self.port = int(self.config.server["dtls"]["port"])
                self.timeout = int(self.config.server["dtls"]["timeout"])
                self.name = "DTLS SERVER"
            else:
                self.port = int(self.config.server["dtls_echo"]["port"])
                self.timeout = int(self.config.server["dtls_echo"]["timeout"])
                self.name = "DTLS ECHO SERVER"

        self.local_ip = "0.0.0.0"

    def get_file(self, path):
        """Parse path and return file."""
        for file_type in self.config.keys():
            if file_type in path:
                path = os.path.join(self.root, "files", path)
                break
        else:
            path = os.path.join(self.root, path)
        if not os.path.exists(path):
            return str.encode("Incorrect path {}\n".format(path))
        if not os.path.isfile(path):
            return str.encode("Given path is not a regular file {}\n".format(path))
        with open(path, "rb") as f:
            flog.info("Sending file {}".format(path))
            return f.read()

    def send_file(self, data, addr):
        """Send file.

        File must be split into smaller packets and sent."""
        data_size = len(data)
        increments = 1024
        for section in range(0, data_size, increments):
            self.sock.sendto(data[section : (section + increments)], addr)
            # Sleep between packet sends
            time.sleep(0.001)

    def run(self):
        """Run UDP server."""
        self.udp_server = socket(AF_INET, SOCK_DGRAM)
        # bind udp socket
        flog.info("{}: starting server on {}".format(self.name, self.port))
        self.udp_server.bind((self.local_ip, self.port))
        if self.secure is True:
            # Wrap the socket
            self.sock = dtls_wrapper.wrap_server(self.udp_server, keyfile=self.privkey,
                                                 certfile=self.fullchain,
                                                 do_handshake_on_connect=True)
            self.sock.settimeout(self.timeout)
            self.sock.listen(5)
        else:
            self.sock = self.udp_server
        flog.debug("{}: Waiting for client connection".format(self.name))
        while True:
            # listen for udp
            try:
                data, addr = self.sock.recvfrom(self.port)
            except Exception as e:
                continue
            flog.debug("{}: Received UDP from client {} : {} ".format(self.name, addr, data))
            if data:
                if self.echo is True:
                    self.sock.sendto(data, addr)
                else:
                    try:
                        request = data.decode("utf-8")
                    except Exception as ex:
                        flog.error("Error decoding data from {} : Exception {}".format(addr, ex))
                        continue
                    data = self.get_file(path=request.strip())
                    self.send_file(data, addr)


def run_server(config_file=CONFIG):
    """Run udp server."""
    flog.info("Starting UDP server")
    config = ConfigHandler(config_file)
    udp_server = UdpServer(config, secure=False)
    udp_dtls_server = UdpServer(config, secure=True)
    dtls_echo_server = UdpServer(config, secure=True, echo=True)
    flog.info("Launch UDP server thread.")
    udp_server_thread = threading.Thread(target=udp_server.run, args=())
    udp_server_thread.start()
    flog.info("Launch UDP DTLS server thread.")
    dtls_server_thread = threading.Thread(target=udp_dtls_server.run, args=())
    dtls_server_thread.start()
    flog.info("Launch DTLS Echo server thread.")
    dtls_echo_server_thread = threading.Thread(target=dtls_echo_server.run, args=())
    dtls_echo_server_thread.start()
    udp_server_thread.join()
    dtls_server_thread.join()
    dtls_echo_server_thread.join()



if __name__ == "__main__":
    run_server()
