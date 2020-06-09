"""Publish port configuration to external api."""
import os
import json
import flog
from config_handler import ConfigHandler


CONFIG = "$FLAKE_TOOLS/host/config/network_emulation.json"


class PortConfiguration:
    """Data file class for handling data files."""

    def __init__(self, config):
        """Initialize port data."""
        self.config = config
        self.port_config = config.server["api"]["ports"]["location"]
        self.port_config = os.path.expandvars(self.port_config)
        self._clear_port_config()
        self.ports = self.parse_config()

    def _clear_port_config(self):
        """Remove data folder tree."""
        if os.path.exists(self.port_config):
            os.remove(self.port_config)

    def parse_config(self):
        """Parse port config file."""
        ports_data = {
            "http": {},
            "https": {},
            "udp": {},
        }
        for setup in self.config.values():
            loss = setup["packet_loss"]
            for key in ports_data.keys():
                ports_data[key][loss] = {}
            for delay, ports in zip(setup["packet_delay"], setup["ports"]):
                for key in ports_data.keys():
                    ports_data[key][loss][delay] = {"port": ports[key]}
        return ports_data

    def publish(self):
        """Publish ports to file."""
        with open(self.port_config, "w") as f:
            json.dump(self.ports, f, indent=2)


def publish_ports(config_file=CONFIG):
    """Configure server files."""
    config = ConfigHandler(config_file)
    port_handler = PortConfiguration(config)
    flog.info("Publishing ports")
    port_handler.publish()
