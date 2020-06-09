"""Traffic control module to configure tc rules on server."""
import os
import flog
from config_handler import ConfigHandler


CONFIG = "$FLAKE_TOOLS/host/config/network_emulation.json"


class TrafficControl:
    """Traffic control class to handle tc rules."""

    def __init__(self, config, root=True):
        """Initialize traffic control handler."""
        self.config = config
        self.dev = config.server["dev"]
        self.root = root
        self.index = 0

    def run(self, cmd):
        """Run traffic control command."""
        tc_cmd = "sudo tc %s" if self.root else "tc %s"
        cmd = tc_cmd % cmd
        flog.debug(cmd)
        os.system(cmd)

    def _create_htb(self):
        """Create htb class."""
        self.run(cmd="qdisc add dev {dev} root handle 1: htb".format(dev=self.dev))

    def clear_htb(self):
        """Clear htb class."""
        self.run(cmd="qdisc del dev {dev} root htb".format(dev=self.dev))

    def _create_htb_class(self, class_id, rate="1000mbit"):
        """Create htb class to hold rules."""
        self.run(
            "class add dev {dev} parent 1: classid 1:{class_id} htb rate {rate}".format(
                dev=self.dev, class_id=class_id, rate=rate
            )
        )

    def _add_port_filter(self, class_id, port):
        """Add filter to class to catch packets on port."""
        self.run(
            "filter add dev {dev} parent 1: protocol ip prio 1 u32 flowid 1:{class_id} match ip dport {port} 0xffff".format(
                dev=self.dev, class_id=class_id, port=port,
            )
        )
        self.run(
            "filter add dev {dev} parent 1: protocol ip prio 1 u32 flowid 1:{class_id} match ip sport {port} 0xffff".format(
                dev=self.dev, class_id=class_id, port=port,
            )
        )

    def _add_packet_rule(self, class_id, packet_delay, packet_loss):
        """Add packet loss to rule."""
        self.run(
            "qdisc add dev {dev} parent 1:{class_id} netem delay {delay} loss {loss}".format(
                dev=self.dev, class_id=class_id, delay=packet_delay, loss=packet_loss,
            )
        )

    def add_rule(
        self, class_id, port, packet_delay=None, packet_loss=None, rate="1000mbit"
    ):
        """Add rule for packet delay and packet loss."""
        self._create_htb_class(class_id, rate)        
        if isinstance(port, dict):
            for p in port.values():
                self._add_port_filter(class_id, p)
        else:
            self._add_port_filter(class_id, port)
        self.run("qdisc show dev {dev}".format(dev=self.dev))

    def show_rules(self):
        """Print rules to console."""
        flog.info("Rules:")
        self.run("qdisc show dev {dev}".format(dev=self.dev))

    def configure(self):
        """Configure server based on config rules."""
        # Reset current rules
        self.clear_htb()
        self._create_htb()
        for name, setup in self.config.items():
            flog.info("Configuring for set: {name}".format(name=name))
            flog.info(
                "Packet delays: {delay}, Packet loss: {loss}, Ports: {ports}".format(
                    delay=setup["packet_delay"],
                    loss=setup["packet_loss"],
                    ports=setup["ports"],
                )
            )
            for delay, ports in zip(setup["packet_delay"], setup["ports"]):
                self.index += 1
                self.add_rule(
                    port=ports,
                    class_id=self.index,
                    packet_loss=setup["packet_loss"],
                    packet_delay=delay,
                )


def configure_server_rules(config_file=CONFIG):
    """Configure server rules."""
    config = ConfigHandler(config_file)
    tc_manager = TrafficControl(config)
    tc_manager.configure()
    tc_manager.show_rules()


def clear_rules(config_file=CONFIG):
    """Wipe server rules."""
    config = ConfigHandler(config_file)
    TrafficControl(config).clear_htb()
