"""Flake server control script."""
import os
import argparse
from enum import Enum
import file_manager
import port_publisher
import traffic_manager
import iperf3_manager
import pcap_manager
import flog


SERVER_ROOT = os.path.expandvars("$FLAKE_SERVER")
SERVER_TOOLS = os.path.expandvars("$FLAKE_TOOLS")


class ServerAction(Enum):
    """Enum to hold server actions."""

    configure = "configure"
    test = "test"


class Server:
    """Server handler class."""

    def __init__(self):
        """Initialize server handler."""
        global SERVER_ROOT, SERVER_TOOLS
        self.server_root = SERVER_ROOT
        self.server_tools = SERVER_TOOLS
        self.config = os.path.join(self.server_root, "nginx.conf")

    def test_config(self):
        """Test nginx config file."""
        cmd = "nginx -t -c {}".format(self.config)
        return os.system(cmd) == 0

    def configure(self, force=False):
        """Configure server at startup."""
        flog.info("---- Configuring Flake ----")
        assert self.add_files(force), "Failed to add files."
        flog.info("---- Successfully added files ----")
        assert port_publisher.publish_ports(), "Failed to publish ports."
        flog.info("---- Successfully published ports ----")
        assert (
            traffic_manager.configure_server_rules()
        ), "failed to configure traffic rules."
        flog.info("---- Successfully configured traffic rules ----")
        assert self.start_udp_server(), "failed to start UDP server."
        flog.info("---- Successfully started UDP server ----")
        assert iperf3_manager.start_iperf(), "failed to start iperf server."
        flog.info("---- Successfully started iperf on server ----")
        assert pcap_manager.start_pcap(), "failed to start pcap."
        flog.info("---- Successfully started pcap on server ----")
        return True

    def add_files(self, force=False):
        """Add server files."""
        try:
            file_manager.configure_files(force)
            return True
        except Exception as e:
            flog.error(e)
            return False

    def start_udp_server(self):
        """Start udp server as background process."""
        script_path = os.path.join(self.server_tools, "host/udp_server.py")
        log_file = os.path.expandvars("$FLAKE_SERVER/logs/udp_server.log")
        cmd = "python3 -u {} > {} &".format(script_path, log_file)
        return os.system(cmd) == 0

    def run_action(self, action, config_file=None, force=False):
        """Run action."""
        action = ServerAction[action]
        if action == ServerAction.test:
            result = self.test_config()
        elif action == ServerAction.configure:
            result = self.configure(force)
        return 0 if result else 1


def main():
    """Parse arguments."""
    parser = argparse.ArgumentParser(description="Flake Legato CLI Tool.")
    parser.add_argument(
        "action",
        type=str,
        help="action for flake server",
        choices=["configure", "test"],
    )
    parser.add_argument("-f", "--force", action="store_true", help="force action")

    args = parser.parse_args()
    server_manager = Server()
    return server_manager.run_action(action=args.action, force=args.force)


if __name__ == "__main__":
    exit(main())
