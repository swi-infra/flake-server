"""Pcap control module to configure pcap on server."""
import os
import shutil
import subprocess
import flog
from config_handler import ConfigHandler


CONFIG = "$FLAKE_TOOLS/host/config/network_emulation.json"


class PcapHandler:
    """Pcap handler."""

    def __init__(self, config):
        """Initialize Pcap handler."""
        self.config = config
        self.server = config.server
        self.script = os.path.expandvars("$FLAKE_TOOLS/host/pcap_listener.py")
        self.dev = self.get_dev()
        self.ports = self.get_ports()
        self.timeout = self.server["pcap"]["timeout"]
        self.rotation_len = self.server["pcap"]["log_rotation_length"]
        self.clean()

    def clean(self):
        """Clean system before starting."""
        try:
            os.system("pkill tcpdump")
        except OSError:
            pass
        if os.path.exists(self.listener_log_dir):
            shutil.rmtree(self.listener_log_dir, ignore_errors=True)
        if os.path.exists(self.pcap_log_dir):
            shutil.rmtree(self.pcap_log_dir, ignore_errors=True)

    @property
    def listener_log_dir(self):
        """Listener log directory."""
        log_dir = os.path.expandvars(self.server["pcap"]["listener_log"])
        self.make_dir(log_dir)
        return log_dir

    @property
    def pcap_log_dir(self):
        """Listener log directory."""
        log_dir = os.path.expandvars(self.server["pcap"]["log"])
        self.make_dir(log_dir)
        return log_dir

    @staticmethod
    def make_dir(directory):
        """Check if directory exists, if not make it."""
        if not os.path.exists(directory):
            os.makedirs(directory)

    @staticmethod
    def get_dev():
        """Get interface device."""
        cmd = "ip route | grep default | awk '{print $5}'"
        flog.debug(cmd)
        rsp = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
        flog.debug("dev: {}".format(rsp))
        return rsp

    def get_listener_log_file(self, scheme, port):
        """Return listener log file."""
        log_file = "{}_pcap_listener_{}.log".format(scheme, port)
        return os.path.join(self.listener_log_dir, log_file)

    def get_tmp_log(self, scheme, port):
        """Return listener log file."""
        log_file = "{}_pcap_listener_{}.pcap".format(scheme, port)
        log_file = os.path.join("/tmp", log_file)
        if os.path.exists(log_file):
            os.remove(log_file)
        return log_file

    def get_ports(self):
        "Return list of ports used."
        port_data = {"tcp": {}, "udp": {}}
        for loss_set in self.config.values():
            for port_list in loss_set["ports"]:
                for scheme, port in port_list.items():
                    if scheme == "udp":
                        port_data["udp"][port] = {"headers_only": False}
                    elif scheme == "iperf":
                        port_data["udp"][port] = {"headers_only": True}
                        port_data["tcp"][port] = {"headers_only": True}
                    elif scheme == "tcp_udp":
                        port_data["udp"][port] = {"headers_only": False}
                        port_data["tcp"][port] = {"headers_only": False}
                    else:
                        port_data["tcp"][port] = {"headers_only": False}
        return port_data

    def run_cmd(self, cmd):
        """Run pcap command."""
        flog.debug(cmd)
        assert os.system(cmd) == 0, "Failed to start pcap"

    def configure_pcap(self):
        """Configure pcap command."""
        pcap_listener_cmd = (
            "python3 -u {script} "
            "--dev {dev} "
            "--scheme {scheme} "
            "--port {port} "
            "--log_dir {log_dir} "
            "--tmp_log {tmp_log} "
            "--timeout {timeout} "
            "--rotation_len {rotation_len} "
            "--headers_only {headers_only} "
            "> {listener_log} 2>&1 &"
        )
        for scheme, port_data in self.ports.items():
            for port, port_info in port_data.items():
                listener_log_path = self.get_listener_log_file(scheme, port)
                tmp_log = self.get_tmp_log(scheme, port)
                cmd = pcap_listener_cmd.format(
                    script=self.script,
                    dev=self.dev,
                    scheme=scheme,
                    port=port,
                    log_dir=self.pcap_log_dir,
                    tmp_log=tmp_log,
                    timeout=self.timeout,
                    rotation_len=self.rotation_len,
                    listener_log=listener_log_path,
                    headers_only=port_info["headers_only"],
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
    """Start pcap listener on server."""
    flog.info("Starting pcap")
    config = ConfigHandler(config_file)
    pcap_handler = PcapHandler(config)
    return pcap_handler.start()


if __name__ == "__main__":
    start_pcap()
