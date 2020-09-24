"""Pcap listener module."""
import os
import time
import glob
import datetime
import argparse
import signal
import subprocess
from shutil import copyfile
from contextlib import contextmanager
import flog


@contextmanager
def funtion_timeout(time):
    # Register a function to raise a TimeoutError on the signal.
    signal.signal(signal.SIGALRM, raise_timeout)
    # Schedule the signal to be sent after ``time``.
    signal.alarm(time)

    try:
        yield
    except TimeoutError:
        pass
    try:
        # Unregister the signal so it won't be triggered
        # if the timeout is not reached.
        signal.signal(signal.SIGALRM, signal.SIG_IGN)
    except TimeoutError:
        pass


def raise_timeout(signum, frame):
    raise TimeoutError


def is_timeout(alt_time, timeout):
    """Check if timeout is reached."""
    return alt_time and time.time() - alt_time >= timeout


def delete_pcap_processes(cmd):
    """Delete Previous PCAP processes."""
    flog.debug("Deleting Previous PCAP processses.")
    command = 'ps -ef | grep "{}"'.format(cmd)
    ps_output = os.popen(command).read()
    print(ps_output)
    if ps_output.count(cmd) > 2:
        tail_pid = int(ps_output.split()[1])
        parent_pid = int(ps_output.split()[2])
        flog.debug("Previous Tail ID: {}".format(tail_pid))
        flog.debug("Previous Parent ID: {}".format(parent_pid))
        if tail_pid is not None:
            flog.debug("Killing Tail PID: {}".format(tail_pid))
            flog.debug("Killing Parent PID: {}".format(parent_pid))
            os.kill(tail_pid, signal.SIGTERM)
            os.kill(parent_pid, signal.SIGTERM)


class PcapListener:
    """Pcap listener class."""

    def __init__(
        self,
        dev,
        scheme,
        port,
        log_dir,
        tmp_log,
        timeout=10,
        rotation_len=10,
        headers_only=False,
    ):
        """Initialize pcap listener."""
        self.dev = dev
        self.scheme = scheme
        self.port = port
        self.log_dir = log_dir
        self.tmp_log = tmp_log
        self.timeout = timeout
        self.rotation_len = rotation_len
        self.headers_only = headers_only
        # Run variables
        self.clear_vars()

    def clear_vars(self):
        """Clear run variables."""
        self.listener_process = None
        self.pcap_process = None
        self.pcap_started = False
        self.last_received_packet = None

    def get_logs(self):
        """Get sorted list of log files based on date modified."""
        log_files = os.path.join(self.log_dir, "*.pcap")
        files = glob.glob(log_files)
        files.sort(key=os.path.getmtime, reverse=True)
        return files

    def rotate_logs(self):
        """Remove old logs from directory."""
        log_list = self.get_logs()
        for log in log_list[self.rotation_len :]:
            flog.debug("Removing old log: {}".format(log))
            os.remove(log)

    def kill_listener(self):
        """Kill listener processes."""
        tcpdump_pid = self.pcap_process.pid
        tail_pid = self.listener_process.pid
        while tcpdump_pid is not None:
            os.kill(tcpdump_pid, signal.SIGTERM)
        while tail_pid is not None:
            os.kill(tail_pid, signal.SIGTERM)

    def create_listener_process(self):
        """Create pcap process and pcap listener."""
        self.open_pcap_process()
        cmd = "tail -c +1 -f {}".format(self.tmp_log)
        flog.debug("listener command: {}".format(cmd))
        delete_pcap_processes(cmd)
        while not os.path.exists(self.tmp_log):
            continue
        self.listener_process = subprocess.Popen(
            cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

    def open_pcap_process(self):
        """Open pcap process."""
        cmd = "/usr/sbin/tcpdump {scheme} -i {dev} port {port} -w {log}".format(
            scheme=self.scheme, dev=self.dev, port=self.port, log=self.tmp_log
        )
        if self.headers_only:
            cmd += " -s 96"
        flog.debug("pcap process command: {}".format(cmd))
        self.pcap_process = subprocess.Popen(cmd.split())

    def get_log_file(self):
        """Return pcap log file."""
        date = datetime.datetime.now()
        date = date.strftime("%Y-%m-%d_%H:%M:%S")
        log_file = "{port}_{date}.pcap".format(port=self.port, date=date)
        directory = os.path.join(self.log_dir, self.port, self.scheme)
        os.makedirs(directory)
        return os.path.join(directory, log_file)

    def save_pcap(self, log_file):
        """Save pcap to log file."""
        copyfile(self.tmp_log, log_file)
        self.rotate_logs()
        os.remove(self.tmp_log)

    def run(self):
        """Run pcap."""
        flog.info("Creating pcap listener process")
        self.create_listener_process()
        while self.listener_process.poll() is None:
            out = ""
            # Scan listener packet input for 1 second
            with funtion_timeout(1):
                out = self.listener_process.stdout.readline()
            if out:
                if not self.pcap_started:
                    flog.info("Capture started...")
                    log_file = self.get_log_file()
                    self.pcap_started = True
                # Reset time
                self.last_received_packet = time.time()
            # Check if timeout reached between packet inputs
            if self.pcap_started and is_timeout(
                self.last_received_packet, self.timeout
            ):
                flog.info("Capture done.")
                self.kill_listener()
                self.clear_vars()
                flog.info("Saving pcap to log file: {}".format(log_file))
                self.save_pcap(log_file)
                self.create_listener_process()
        flog.warning(self.listener_process.communicate())


def start_cap():
    parser = argparse.ArgumentParser(description="Pcap listener.")
    parser.add_argument("--dev", type=str, help="Network device", required=True)
    parser.add_argument(
        "--scheme", type=str, help="Scheme", choices=["tcp", "udp"], required=True
    )
    parser.add_argument("--port", type=str, help="Port", required=True)
    parser.add_argument("--log_dir", type=str, help="Log directory", required=True)
    parser.add_argument(
        "--tmp_log", type=str, help="Temporary log file for listener", required=True
    )
    parser.add_argument("--timeout", type=int, help="Timeout", default=10)
    parser.add_argument(
        "--rotation_len", type=int, help="Number of logs to rotate", default=10
    )
    parser.add_argument(
        "--headers_only",
        type=str,
        help="Only capture packet header",
        choices=["True", "False"],
        default="False",
    )
    args = parser.parse_args()
    args.headers_only = eval(args.headers_only)
    flog.debug(args)
    pcap_listener = PcapListener(**vars(args))
    pcap_listener.run()
    flog.error("RUN ENDED")


if __name__ == "__main__":
    start_cap()
