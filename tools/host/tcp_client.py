#!/usr/bin/env python3
"""TCP client tool."""
import _thread
from socket import socket, AF_INET, SOCK_STREAM
import flog
from config_handler import ServerConfig
from http.server import BaseHTTPRequestHandler, HTTPServer
import cgi


MAX_BUFFER = 65535
DEFAULT_TIMEOUT = 120


class EchoClient:
    """TCP client class."""

    def __init__(
        self,
        address,
        port,
        message="Hello from Flake Client!",
        echo=False,
        timeout=DEFAULT_TIMEOUT,
    ):
        """Initialize TCP server."""
        self.address = address
        self.port = port
        self.message = message
        self.echo = echo
        self.timeout = timeout
        self.tcp_client = socket(AF_INET, SOCK_STREAM)
        self.tcp_client.settimeout(self.timeout)

    def send(self, data):
        """Send encoded data to server."""
        try:
            self.tcp_client.sendall(data)
        except (BlockingIOError, ConnectionResetError, socket.timeout) as e:
            flog.debug(e)

    def receive(self):
        """Receive encoded data from server."""
        try:
            data = self.tcp_client.recv(MAX_BUFFER)
            flog.debug("Received message of length: %s bytes" % len(data))
            return data
        except (BlockingIOError, ConnectionResetError, socket.timeout) as e:
            flog.debug(e)
        return None

    def run(self):
        """Run TCP client."""
        flog.info("Connecting to tcp server at {}:{}".format(self.address, self.port))
        self.tcp_client.connect((self.address, self.port))

        while True:
            try:
                if self.echo:
                    data = self.receive()
                    if not data:
                        self.tcp_client.close()
                        break
                    self.send(data)
                else:
                    self.send(self.message.encode())
                    data = self.receive()
                    if not data:
                        self.tcp_client.close()
                        break
            except Exception as ex:
                flog.warning("TCP Client Exception: {}".format(ex))
                self.tcp_client.close()
                break
        flog.info("End TCP Client")


class RequestHandler(BaseHTTPRequestHandler):
    """Handle http requests."""

    def _set_headers(self):
        """Set header type."""
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def do_HEAD(self):
        """Call set headers."""
        self._set_headers()

    def do_GET(self):
        """Return usage."""
        self._set_headers()
        self.wfile.write(
            b"<html><body><h1>Usage, POST request: http://flake.legato.io:(port)?server=(ip)&port=(port)&message=(str)&echo=(1/0)</h1></body></html>"
        )

    def do_POST(self):
        """Start TCP client from request."""
        self._set_headers()
        form = cgi.FieldStorage(
            fp=self.rfile, headers=self.headers, environ={"REQUEST_METHOD": "POST"}
        )
        request_vals = {
            "server": form.getvalue("server", None),
            "port": form.getvalue("port", None),
            "message": form.getvalue("message", "Hello from Flake Client!"),
            "echo": form.getvalue("echo", False),
        }
        if not (
            request_vals["server"]
            and request_vals["port"]
            and request_vals["port"].isdigit()
            and (request_vals["message"] or request_vals["echo"])
        ):
            self.wfile.write(b"<html><body><h1>Bad Request!</h1></body></html>")
            return

        self.wfile.write(
            b"<html><body><h1>Request Received, starting tcp client!</h1></body></html>"
        )
        echo_client = EchoClient(
            address=request_vals["server"],
            port=int(request_vals["port"]),
            message=request_vals["message"],
            echo=request_vals["echo"],
        )
        flog.info("Starting tcp thread.")
        _thread.start_new_thread(echo_client.run, ())


class HttpTCPRequestServer:
    """Http TCP request server class."""

    def __init__(self, config):
        """Initialize http server."""
        global DEFAULT_TIMEOUT
        self.config = config
        try:
            self.port = int(self.config["tcp_client"]["port"])
        except (KeyError, ValueError) as e:
            flog.error("Could not get port for tcp_client.")
            raise e
        try:
            DEFAULT_TIMEOUT = int(self.config["tcp_udp"]["timeout"])
        except (KeyError, ValueError):
            flog.warning(
                "Could not use specified timeout, using default value: %d"
                % DEFAULT_TIMEOUT
            )
        self.address = ("0.0.0.0", self.port)

    def run(self):
        """Run http server."""
        httpd = HTTPServer(self.address, RequestHandler)
        flog.info("Server running at localhost:%d..." % self.port)
        httpd.serve_forever()


def main():
    """Run Http TCP server."""
    flog.info("Starting Server")
    config = ServerConfig()
    server = HttpTCPRequestServer(config=config)
    server.run()


if __name__ == "__main__":
    main()
