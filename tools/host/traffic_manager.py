"""Traffic control module to configure tc rules on server."""
import os
import subprocess
import flog
from config_handler import ConfigHandler


CONFIG = "$FLAKE_TOOLS/host/config/network_emulation.json"


class TrafficControl:
    """Traffic control class to handle tc rules."""

    def __init__(self, config):
        """Initialize traffic control handler."""
        self.config = config
        self.server_config = config.server
        self.dev = self._get_dev()
        self.index = 0

    def run(self, cmd, tc=True, output=False):
        """Run traffic control command."""
        pre_cmd = "tc {}" if tc else "{}"
        cmd = pre_cmd.format(cmd)
        flog.debug(cmd)
        if output:
            return subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
        return os.system(cmd) == 0

    def _get_dev(self):
        cmd = "ip route | grep default | awk '{print $5}'"
        rsp = self.run(cmd, tc=False, output=True)
        flog.debug("dev: {}".format(rsp))
        return rsp

    def accept_ports(self, scheme, ports):
        """Accept ports via iptables."""
        protocol = "tcp" if "http" in scheme else "udp"
        cmd = "iptables -I INPUT -p {protocol} --match multiport --dport {ports} -j ACCEPT"
        ports_list = ",".join(ports)
        cmd = cmd.format(ports=ports_list, protocol=protocol)
        return self.run(cmd, tc=False)

    def redirect_ports(self, scheme, src_list, dst):
        """Redirect ports via iptables."""
        protocol = "tcp" if "http" in scheme else "udp"
        cmd = (
            "iptables -t nat -I PREROUTING -p {protocol} "
            "--match multiport --dport {ports} -j REDIRECT --to-port {dst}"
        )
        ports_list = ",".join(src_list)
        cmd = cmd.format(protocol=protocol, ports=ports_list, dst=dst)
        return self.run(cmd, tc=False)

    def show_ip_tables(self):
        """Show ip tables rules."""
        flog.info("IP Table Rules:")
        flog.info(self.run("iptables -n -L --line-numbers", tc=False, output=True))
        flog.info(
            self.run("iptables -t nat -n -L --line-numbers", tc=False, output=True)
        )

    def add_ip_tables(self):
        """Add ip table rules.

        Accepts incoming traffic on ports.
        Redirects traffic on simulation ports to default ports.
        Configuration specified in server config.
        """
        flog.info("Accepting ports")
        for scheme, port_set in self.server_config["ports"].items():
            if not self.accept_ports(scheme=scheme, ports=port_set):
                return False
        flog.info("Redirecting ports")
        for scheme, port_list in self.server_config["ports"].items():
            if not self.redirect_ports(
                scheme=scheme, src_list=port_list[1:], dst=port_list[0]
            ):
                return False
        self.show_ip_tables()
        return True

    def _create_htb(self):
        """Create htb class."""
        return self.run(
            cmd="qdisc add dev {dev} root handle 1: htb".format(dev=self.dev)
        )

    def clear_htb(self):
        """Clear htb class."""
        self.run(cmd="qdisc del dev {dev} root htb".format(dev=self.dev))

    def _create_htb_class(self, class_id, rate="1000mbit"):
        """Create htb class to hold rules."""
        return self.run(
            "class add dev {dev} parent 1: classid 1:{class_id} htb rate {rate}".format(
                dev=self.dev, class_id=class_id, rate=rate
            )
        )

    def _add_port_filter(self, class_id, port):
        """Add filter to class to catch packets on port."""
        if not self.run(
            "filter add dev {dev} parent 1: protocol ip prio 1 u32 flowid 1:{class_id} match ip dport {port} 0xffff".format(
                dev=self.dev, class_id=class_id, port=port
            )
        ):
            return False
        return (
            self.run(
                "filter add dev {dev} parent 1: protocol ip prio 1 u32 flowid 1:{class_id} match ip sport {port} 0xffff".format(
                    dev=self.dev, class_id=class_id, port=port
                )
            ),
            "failed to add filter.",
        )

    def _add_packet_rule(self, class_id, packet_delay, packet_loss):
        """Add packet loss to rule."""
        return self.run(
            "qdisc add dev {dev} parent 1:{class_id} netem delay {delay} loss {loss}".format(
                dev=self.dev, class_id=class_id, delay=packet_delay, loss=packet_loss
            )
        )

    def add_rule(
        self, class_id, port, packet_delay="0ms", packet_loss="0%", rate="1000mbit"
    ):
        """Add rule for packet delay and packet loss."""
        if not self._create_htb_class(class_id, rate):
            return False
        if isinstance(port, dict):
            for p in port.values():
                if not self._add_port_filter(class_id, p):
                    return False
        else:
            if not self._add_port_filter(class_id, port):
                return False
        return self._add_packet_rule(class_id, packet_delay, packet_loss)

    def show_rules(self):
        """Print rules to console."""
        flog.info("Traffic Control Rules:")
        flog.info(self.run("qdisc show dev {dev}".format(dev=self.dev), output=True))
        return True

    def configure(self):
        """Configure server based on config rules."""
        assert self.add_ip_tables(), "Failed to add to ip tables"
        # Reset current rules
        self.clear_htb()
        assert self._create_htb(), "Failed to create htb"
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
                assert self.add_rule(
                    port=ports,
                    class_id=self.index,
                    packet_loss=setup["packet_loss"],
                    packet_delay=delay,
                ), "Failed to set rule"


def configure_server_rules(config_file=CONFIG):
    """Configure server rules."""
    config = ConfigHandler(config_file)
    try:
        tc_manager = TrafficControl(config)
        tc_manager.configure()
        tc_manager.show_rules()
        return True
    except AssertionError as e:
        flog.error(e)
        return False


def clear_rules(config_file=CONFIG):
    """Wipe server rules."""
    config = ConfigHandler(config_file)
    TrafficControl(config).clear_htb()
    return True
