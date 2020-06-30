"""Pcap control module to configure pcap on server."""
import os
import flog
from config_handler import ConfigHandler


CONFIG = "$FLAKE_TOOLS/host/config/network_emulation.json"


class Pcap:
    """Pcap handler."""

    def __init__(self, config):
        """Initialize Pcap handler."""
        self.config = config
        self.server = config.server
        self.log_dir = os.path.expandvars(self.server["pcap"]["log"])
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        self.log_size = os.path.expandvars(self.server["pcap"]["log_size"])
        self.ports = self.get_ports()

    def get_ports(self):
        "Return list of ports used."
        ports = {"tcp": [], "udp": []}
        for loss_set in self.config.values():
            for port_list in loss_set["ports"]:
                for scheme, port in port_list.items():
                    if scheme == "udp":
                        ports["udp"].append(port)
                    else:
                        ports["tcp"].append(port)
        return ports

    def run_cmd(self, cmd):
        """Run pcap command."""
        flog.debug(cmd)
        assert os.system(cmd) == 0, "Failed to start pcap"

    def configure_pcap(self):
        """Configure pcap command."""
        pcap_cmd = "tcpdump {scheme} port {port} -W 1 -C {size} -w {log} &"
        for scheme, ports in self.ports.items():
            for port in ports:
                log_path = os.path.join(self.log_dir, "pcap_{}.pcap".format(port))
                if scheme in ("udp", "iperf"):
                    cmd = pcap_cmd.format(
                        scheme="udp", port=port, size=self.log_size, log=log_path
                    )
                    self.run_cmd(cmd)
                if scheme != "udp":
                    cmd = pcap_cmd.format(
                        scheme="", port=port, size=self.log_size, log=log_path
                    )
                    self.run_cmd(cmd)

    def start(self):
        """Start pcap."""
        try:
            self.configure_pcap()
            return True
        except AssertionError as e:
            flog.error(e)
            return False


def start_pcap(config_file=CONFIG):
    """Start pcap on server."""
    flog.info("Starting pcap")
    config = ConfigHandler(config_file)
    pcap_handler = Pcap(config)
    return pcap_handler.start()
