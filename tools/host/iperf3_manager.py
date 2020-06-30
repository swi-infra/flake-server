"""Iperf3 control module to configure iperf on server."""
import os
import flog
from config_handler import ConfigHandler


CONFIG = "$FLAKE_TOOLS/host/config/network_emulation.json"


class Iperf:
    """Iperf3 handler."""

    def __init__(self, config):
        """Initialize iperf handler."""
        self.config = config
        self.server = config.server
        self.log_file = os.path.expandvars(self.server["iperf"]["log"])
        self.ports = self.get_ports()

    def get_ports(self):
        "Return list of ports used for iperf."
        ports = []
        for loss_set in self.config.values():
            for port_list in loss_set["ports"]:
                for scheme, port in port_list.items():
                    if scheme == "iperf":
                        ports.append(port)
        return ports

    def run_cmd(self):
        """Run iperf command."""
        iperf_cmd = "iperf3 -s -p {port} >{log_file} 2>&1 &"
        for port in self.ports:
            cmd = iperf_cmd.format(port=port, log_file=self.log_file)
            flog.debug(cmd)
            assert os.system(cmd) == 0, "Failed to start iperf"

    def start(self):
        """Start iperf."""
        try:
            os.system("killall iperf3")
            self.run_cmd()
            return True
        except AssertionError as e:
            flog.error(e)
            return False


def start_iperf(config_file=CONFIG):
    """Start iperf on server."""
    flog.info("Starting iperf")
    config = ConfigHandler(config_file)
    iperf_handler = Iperf(config)
    return iperf_handler.start()
