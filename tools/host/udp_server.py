import os
import time
from socket import socket, AF_INET, SOCK_DGRAM
import flog
from config_handler import ConfigHandler


CONFIG = "$FLAKE_TOOLS/host/config/data_files.json"


class UdpServer:
    """UDP server class."""

    def __init__(self, config):
        """Initialize udp server."""
        self.config = config
        self.port = int(self.config.server["udp"]["port"])
        self.buffer = int(self.config.server["udp"]["buffer"])
        self.root = os.path.expandvars("$FLAKE_SERVER/public")
        self.udp_server = socket(AF_INET, SOCK_DGRAM)
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
            return str.encode("Incorrect path {}".format(path))
        with open(path, "rb") as f:
            flog.info("Sending file {}".format(path))
            return f.read()

    def send_file(self, data, addr):
        """Send file.

        File must be split into smaller packets and sent."""
        data_size = len(data)
        increments = 1024
        for section in range(0, data_size, increments):
            self.udp_server.sendto(data[section : (section + increments)], addr)
            # Sleep between packet sends
            time.sleep(0.001)

    def run(self):
        """Run UDP server."""
        # bind udp socket
        flog.debug("starting udp server on {}".format(self.port))
        self.udp_server.bind((self.local_ip, self.port))
        while True:
            # listen for udp
            data, addr = self.udp_server.recvfrom(self.port)
            flog.debug("Received UDP: {}".format(data))
            if data:
                request = data.decode("utf-8")
                data = self.get_file(path=request)
                self.send_file(data, addr)


def run_server(config_file=CONFIG):
    """Run udp server."""
    flog.info("Starting UDP server")
    config = ConfigHandler(config_file)
    udp_server = UdpServer(config)
    udp_server.run()


if __name__ == "__main__":
    run_server()
