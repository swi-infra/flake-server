#!/usr/bin/env python3
"""Publish port configuration to external api."""
import os
import json
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
        }
        for setup in self.config.values():
            loss = setup["packet_loss"]
            ports_data["http"][loss] = {}
            ports_data["https"][loss] = {}
            for delay, ports in zip(setup["packet_delay"], setup["ports"]):
                ports_data["http"][loss][delay] = {"port": ports[0]}
                ports_data["https"][loss][delay] = {"port": ports[1]}
        return ports_data

    def publish(self):
        """Publish ports to file."""
        with open(self.port_config, "w") as f:
            json.dump(self.ports, f, indent=2)


def publish_ports(config_file):
    """Configure server files."""
    config = ConfigHandler(config_file)
    port_handler = PortConfiguration(config)
    port_handler.publish()


if __name__ == "__main__":
    publish_ports(CONFIG)
