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
        flog.debug("Clearing port config.")
        if os.path.exists(self.port_config):
            os.remove(self.port_config)

    def parse_config(self):
        """Parse port config file."""
        ports_data = {}
        for setup in self.config.values():
            loss = setup["packet_loss"]
            services = setup["ports"][0].keys()
            for key in services:
                if key not in ports_data.keys():
                    ports_data[key] = {loss: {}}
                else:
                    ports_data[key][loss] = {}
            for delay, ports in zip(setup["packet_delay"], setup["ports"]):
                for key, val in ports.items():
                    ports_data[key][loss][delay] = {"port": val}
        return ports_data

    def publish(self):
        """Publish ports to file."""
        try:
            flog.debug("Publishing ports to file.")
            flog.debug("Ports: {}".format(self.ports))
            with open(self.port_config, "w") as fd:
                json.dump(self.ports, fd, indent=2)
            return True
        except Exception as e:
            flog.error("Failed to publish ports: {}".format(e))
            return False


def publish_ports(config_file=CONFIG):
    """Configure server files."""
    config = ConfigHandler(config_file)
    port_handler = PortConfiguration(config)
    flog.info("Publishing ports...")
    return port_handler.publish()
