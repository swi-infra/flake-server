"""Traffic control module to configure tc rules on server."""
import os
import subprocess
import socket
from enum import Enum
import flog
from config_handler import ConfigHandler

CONFIG = "$FLAKE_TOOLS/host/config/network_emulation.json"


class Command(Enum):
    """Command enum."""

    Tc = "tc"
    Iptables = "iptables"


class TrafficControl:
    """Traffic control class to handle tc rules."""

    def __init__(self, config):
        """Initialize traffic control handler."""
        self.config = config
        self.server_config = config.server
        self.dev = self._get_dev()
        self.index = 0

    def run(self, command, tool=Command.Tc, output=False):
        """Run traffic control command."""
        cmd = "{} ".format(tool.value) if tool else ""
        cmd += command
        flog.debug(cmd)
        if output:
            return subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
        return os.system(cmd) == 0

    def _get_dev(self):
        cmd = "ip route | grep default | awk '{print $5}'"
        rsp = self.run(cmd, tool=None, output=True)
        flog.debug("dev: {}".format(rsp))
        return rsp

    def accept_ports(self, protocol, ports):
        """Accept ports via iptables."""
        cmd = "-I INPUT -p {protocol} --match multiport --dport {ports} -j ACCEPT"
        ports_list = ",".join(ports)
        cmd = cmd.format(ports=ports_list, protocol=protocol)
        return self.run(cmd, tool=Command.Iptables)

    def redirect_ports(self, protocol, src_list, dst):
        """Redirect ports via iptables."""
        cmd = (
            "-t nat -I PREROUTING -p {protocol} "
            "--match multiport --dport {ports}"
        )
        if "." in dst:
            cmd += " -j DNAT --to-destination {dst}"
        else:
            cmd += " -j REDIRECT --to-port {dst}"
        ports_list = ",".join(src_list)
        cmd = cmd.format(protocol=protocol, ports=ports_list, dst=dst)
        return self.run(cmd, tool=Command.Iptables)

    def show_ip_tables(self):
        """Show ip tables rules."""
        flog.info("IP Table Rules:")
        flog.info(self.run("-n -L --line-numbers", tool=Command.Iptables, output=True))
        flog.info(
            self.run("-t nat -n -L --line-numbers", tool=Command.Iptables, output=True)
        )

    def port_range_to_ports(self, port_set):
        ports = [port_set]
        if ":" in port_set:
            ports = []
            port = int(port_set.split(":")[0])
            max_port = int(port_set.split(":")[1])
            while port < max_port:
                ports.append("%s" % port)
                port += 1
        return ports

    def add_ip_tables(self, host=None):
        """Add ip table rules.

        Accepts incoming traffic on ports.
        Redirects traffic on simulation ports to default ports.
        Configuration specified in server config.
        """
        flog.info("Accepting and redirecting ports (host=%s)" % host)
        if host:
            hostname = os.environ.get("FILTER_HOST", "filter")
            filter_host = socket.gethostbyname(hostname)
            assert host, "Unable to get host from hostname %s" % hostname
            flog.debug("Redirect connections to host %s to %s" % (filter_host, host))
            self.run("-t nat -A POSTROUTING -o eth0 -j SNAT --to-source %s" % filter_host, tool=Command.Iptables)
        for protocol, protocol_set in self.server_config["ports"].items():
            for default_port, port_set in protocol_set.items():
                if default_port != "null":
                    port_set.append(default_port)
                if not self.accept_ports(protocol=protocol, ports=port_set):
                    return False
                if host:
                    default_port = host
                if default_port != "null" and not self.redirect_ports(
                    protocol=protocol, src_list=port_set, dst=default_port
                ):
                    return False
        self.show_ip_tables()
        return True

    def _create_htb(self):
        """Create htb class."""
        return self.run(
            command="qdisc add dev {dev} root handle 1: htb".format(dev=self.dev)
        )

    def clear_htb(self):
        """Clear htb class."""
        self.run(command="qdisc del dev {dev} root htb".format(dev=self.dev))

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

    def _add_tc_packet_rule(self, class_id, packet_delay, packet_loss):
        """Add packet loss to rule (tc)."""
        return self.run(
            "qdisc add dev {dev} parent 1:{class_id} netem delay {delay} loss {loss}".format(
                dev=self.dev, class_id=class_id, delay=packet_delay, loss=packet_loss
            )
        )

    def _add_ip_packet_rule(self, protocol, port, packet_loss):
        """Add packet loss to rule (ip)."""
        return self.run(
            "-t mangle -A PREROUTING -p {protocol} --dport {port} -m statistic --mode random --probability {loss} -j DROP".format(
                protocol=protocol, port=port, loss=float(packet_loss.strip("%")) / 100
            ),
            tool=Command.Iptables,
        )

    def add_egress_rule(
        self, class_id, port, packet_delay="0ms", packet_loss="0%", rate="1000gbit"
    ):
        """Add egress rule for packet delay and packet loss."""
        if not self._create_htb_class(class_id, rate):
            return False
        for p in port.values():
            if not self._add_port_filter(class_id, p):
                return False
        return self._add_tc_packet_rule(class_id, packet_delay, packet_loss)

    def add_ingress_rule(self, port, packet_loss="0%"):
        """Add ingress rule for packet loss."""
        for p in port.values():
            if not self._add_ip_packet_rule(
                "tcp", p, packet_loss
            ) or not self._add_ip_packet_rule("udp", p, packet_loss):
                return False
        return True

    def show_rules(self):
        """Print rules to console."""
        flog.info("Traffic Control Rules:")
        flog.info(self.run("qdisc show dev {dev}".format(dev=self.dev), output=True))
        return True

    def configure(self, with_filtering=True, with_services=True):
        """Configure server based on config rules."""
        host = None
        if not with_services:
            hostname = os.environ.get("SERVICES_HOST", "server")
            host = socket.gethostbyname(hostname)
            assert host, "Unable to get host from hostname %s" % hostname
        assert self.add_ip_tables(host), "Failed to add to ip tables"

        if not with_filtering:
            return

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
                assert self.add_egress_rule(
                    port=ports,
                    class_id=self.index,
                    packet_loss=setup["packet_loss"],
                    packet_delay=delay,
                ), "Failed to set egress rule"
                assert self.add_ingress_rule(
                    port=ports, packet_loss=setup["packet_loss"]
                ), "Failed to set ingress rule"


def configure_server_rules(config_file=CONFIG, with_filtering=True, with_services=True):
    """Configure server rules."""
    config = ConfigHandler(config_file)
    try:
        tc_manager = TrafficControl(config)
        tc_manager.configure(with_filtering=with_filtering, with_services=with_services)
        tc_manager.show_rules()
        return True
    except AssertionError as ex:
        flog.error(ex)
        return False


def clear_rules(config_file=CONFIG):
    """Wipe server rules."""
    config = ConfigHandler(config_file)
    TrafficControl(config).clear_htb()
    return True
