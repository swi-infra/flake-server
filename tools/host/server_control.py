"""Flake server control script."""
import os
import argparse
from enum import Enum
import file_manager
import port_publisher
import traffic_manager
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
        self.cron_config = {}

        self.with_filtering = os.environ.get("FILTER", "1") == "1"
        self.with_services = os.environ.get("SERVICES", "1") == "1"

    def test_config(self):
        """Test nginx config file."""
        cmd = "nginx -t -c {}".format(self.config)
        return os.system(cmd) == 0

    def configure(self, force=False):
        """Configure server at startup."""
        if self.with_services:
            flog.info("---- Configuring Flake ----")
            assert self.add_files(force), "Failed to add files."
            flog.info("---- Successfully added files ----")
            assert port_publisher.publish_ports(), "Failed to publish ports."
            flog.info("---- Successfully published ports ----")
        assert traffic_manager.configure_server_rules(
            with_filtering=self.with_filtering, with_services=self.with_services
        ), "failed to configure traffic rules."
        flog.info("---- Successfully configured traffic rules ----")
        if self.with_services:
            assert self.start_udp_server(), "failed to start UDP server."
            flog.info("---- Successfully started UDP server ----")
            assert self.configure_iperf(), "failed to configure iperf server."
            flog.info("---- Successfully configured iperf on server ----")
            assert self.start_echo_servers(), "failed to start TCP/UDP Echo servers."
            flog.info("---- Successfully started TCP/UDP Echo servers ----")
            assert self.start_tcp_tls_server(), "failed to start TCP TLS server."
            flog.info("---- Successfully started TCP TLS Echo server  ----")
            assert (
                self.start_http_tcp_client_server()
            ), "failed to start http TCP client server."
            flog.info("---- Successfully started http TCP client server  ----")
        assert self.configure_pcap(), "failed to start pcap."
        flog.info("---- Successfully started pcap on server ----")
        assert self.configure_cron(), "failed to start cron."
        flog.info("---- Successfully started cron on server ----")
        return True

    def add_files(self, force=False):
        """Add server files."""
        try:
            file_manager.configure_files(force)
            return True
        except Exception as ex:
            flog.error(ex)
            return False

    def start_udp_server(self):
        """Start udp server as background process."""
        script_path = os.path.join(self.server_tools, "host/udp_server.py")
        log_file = os.path.join(self.server_root, "logs/udp_server.log")
        cmd = "python3 -u {} > {} 2>&1 &".format(script_path, log_file)
        flog.debug("Starting udp server with: {}".format(cmd))
        return os.system(cmd) == 0

    def start_echo_servers(self):
        """Start tcp/udp echo servers as background process."""
        script_path = os.path.join(self.server_tools, "host/echo_servers.py")
        log_file = os.path.join(self.server_root, "logs/echo_servers.log")
        cmd = "python3 -u {} > {} 2>&1 &".format(script_path, log_file)
        flog.debug("Starting udp/tcp echo server with: {}".format(cmd))
        return os.system(cmd) == 0

    def start_tcp_tls_server(self):
        """Start tcp tls echo server as background process."""
        script_path = os.path.join(self.server_tools, "host/tcp_tls_server.py")
        log_file = os.path.join(self.server_root, "logs/tcp_tls_server.log")
        cmd = "python3 -u {} > {} 2>&1 &".format(script_path, log_file)
        flog.debug("Starting tcp tls echo server with: {}".format(cmd))
        return os.system(cmd) == 0

    def start_http_tcp_client_server(self):
        """Start http tcp client server as background process."""
        script_path = os.path.join(self.server_tools, "host/tcp_client.py")
        log_file = os.path.join(self.server_root, "logs/tcp_client.log")
        cmd = "python3 -u {} > {} 2>&1 &".format(script_path, log_file)
        flog.debug("Starting http tcp client server with: {}".format(cmd))
        return os.system(cmd) == 0

    def configure_iperf(self):
        """Configure iperf settings."""
        flog.debug("configuring iperf cron settings.")
        self.cron_config["iperf"] = {
            "script": os.path.join(self.server_tools, "host/iperf3_manager.py"),
            "log_file": os.path.join(self.server_root, "logs/iperf_manager.log"),
        }
        return True

    def configure_pcap(self):
        """Configure pcap settings."""
        flog.debug("configuring pcap_manager cron settings.")
        self.cron_config["pcap"] = {
            "script": os.path.join(self.server_tools, "host/pcap_manager.py"),
            "log_file": os.path.join(self.server_root, "logs/pcap_manager.log"),
        }
        return True

    def configure_cron(self):
        """Configure cron settings."""
        flog.debug("configuring cron")
        env_vars = "PYTHONPATH={} FLAKE_SERVER={} FLAKE_TOOLS={} SHELL=/bin/bash".format(
            os.environ.get("PYTHONPATH"),
            os.environ.get("FLAKE_SERVER"),
            os.environ.get("FLAKE_TOOLS"),
        )
        for cron_script, info in self.cron_config.items():
            script = "python3 -u {} > {} 2>&1".format(info["script"], info["log_file"])
            cmd = "{vars} {script}".format(vars=env_vars, script=script)
            # Restart script every 3 hours.
            cron_cmd = '(crontab -l ; echo "{cron_time} {cmd}") | crontab -'.format(
                cron_time="0 */3 * * *", cmd=cmd
            )
            try:
                # Initial start
                flog.debug(cmd)
                assert os.system(cmd) == 0, "Failed to start {}".format(cron_script)
                # Configure cron
                flog.debug(cron_cmd)
                assert os.system(cron_cmd) == 0, "Failed to configure cron"
            except AssertionError as e:
                flog.error(e)
                return False
        try:
            assert os.system("/etc/init.d/cron restart") == 0, "Failed to start cron"
        except AssertionError as e:
            flog.error(e)
            return False
        return True

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
    flog.info(
        "Server: filtering[%s] services[%s]"
        % (server_manager.with_filtering, server_manager.with_services)
    )
    return server_manager.run_action(action=args.action, force=args.force)


if __name__ == "__main__":
    exit(main())
