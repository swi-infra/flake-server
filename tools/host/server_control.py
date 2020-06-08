"""Flake server control script."""
import os
import signal
import pexpect
import argparse
from enum import Enum
import subprocess
import file_manager
import port_publisher
import traffic_manager
import flog


SERVER_ROOT = os.path.expandvars("$FLAKE_SERVER")


class ServerAction(Enum):
    """Enum to hold server actions."""

    start = "start"
    stop = "stop"
    restart = "restart"
    test = "test"


class Server:
    """Server handler class."""

    def __init__(self):
        """Initialize server handler."""
        global SERVER_ROOT
        self.server_root = SERVER_ROOT
        self.config = os.path.join(self.server_root, "conf/nginx.conf")
        self.pid = os.path.join(self.server_root, "logs/nginx.pid")

    def run(self, action, config_file=None):
        """Run command for server."""
        cmd = "sudo nginx"
        if action == ServerAction.test:
            cmd += " -t"
        cmd += " -p {prefix}".format(prefix=self.server_root)
        if action == ServerAction.stop:
            cmd += " -s {action}".format(action=action.value)
        if config_file:
            config_file = os.path.expandvars(config_file)
        else:
            config_file = self.config
        assert os.path.exists(config_file), "Config file at {} does not exist.".format(
            config_file
        )
        cmd += " -c {config}".format(config=config_file)
        flog.debug(cmd)
        return os.system(cmd) == 0

    def test_config(self, config_file):
        """Test nginx config file."""
        assert self.run(
            ServerAction.test, config_file
        ), "Invalid configuration file {}".format(config_file)

    def start(self, config_file=None, full=False):
        """Start the server."""
        if full:
            file_manager.configure_files()
        port_publisher.publish_ports()
        traffic_manager.configure_server_rules()
        assert self.run(
            ServerAction.start, config_file
        ), "Could not start nginx, maybe a process is already running.\n(try running server stop --force)"

    def stop(self, force=False):
        """Stop the server."""
        if os.path.exists(self.pid):
            flog.info("Stopping nginx using nginx method")
            self.run(ServerAction.stop)
        else:
            flog.warning(
                "Could not stop nginx using nginx method. No such file {}".format(
                    self.pid
                )
            )
            if not force:
                flog.warning("Try using -f/--force.")
            flog.warning("it is possible nginx was not running")
        if force:
            assert self.kill(), "Could not kill nginx"
        traffic_manager.clear_rules()

    def restart(self, config_file=None, force=False, full=False):
        """Restart the server."""
        self.stop(force)
        self.start(config_file, full)

    def kill(self):
        """Kill nginx"""
        try:
            pid_list = subprocess.check_output(
                ["pidof", "nginx"], encoding="utf-8"
            ).split()
        except subprocess.CalledProcessError:
            return True
        for pid in pid_list:
            flog.info("killing nginx with pid of {}".format(pid))
            try:
                os.kill(int(pid), signal.SIGKILL)
            except ProcessLookupError:
                flog.warning("Proccess not found.")
        try:
            pid_list = subprocess.check_output(
                ["pidof", "nginx"], encoding="utf-8"
            ).split()
            flog.error("nginx could not be killed")
            return False
        except subprocess.CalledProcessError:
            return True

    def run_action(self, action, config_file=None, force=False, full=False):
        """Run action."""
        action = ServerAction[action]
        if action == ServerAction.start:
            result = self.start(config_file, full)
        elif action == ServerAction.stop:
            # TODO: ctrl+c calls stop
            result = self.stop(force)
        elif action == ServerAction.restart:
            result = self.restart(config_file, force, full)
        elif action == ServerAction.test:
            result = self.test_config(config_file)
        return result


def main():
    """Parse arguments."""
    parser = argparse.ArgumentParser(description="Flake Legato CLI Tool.")
    parser.add_argument(
        "action", type=str, help="action for flake server [start|stop|restart]"
    )
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        help="path to nginx configuration file (default $FLAKE_SERVER/conf/nginx.conf)",
    )
    parser.add_argument("-f", "--force", action="store_true", help="force action")
    parser.add_argument(
        "--full", action="store_true", help="rebuild files and traffic control rules"
    )

    args = parser.parse_args()
    server_manager = Server()
    return server_manager.run_action(
        action=args.action, config_file=args.config, force=args.force, full=args.full,
    )


if __name__ == "__main__":
    exit(main())
