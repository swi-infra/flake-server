#!/usr/bin/env python3
"""TCP client tool."""
import _thread
import flog
from config_handler import ServerConfig
from echo_client import EchoClient
from http.server import BaseHTTPRequestHandler, HTTPServer
import cgi


DEFAULT_TIMEOUT = 240
LOCAL_PORT_UDP = 50000
SERVICES = ["tcp_client", "udp_client"]


class RequestHandler(BaseHTTPRequestHandler):
    """Handle http requests."""

    def _set_headers(self, rsp=200):
        """Set header type."""
        self.send_response(rsp)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def do_HEAD(self):
        """Call set headers."""
        self._set_headers(200)

    def do_GET(self):
        """Return usage."""
        self._set_headers(200)
        service_string = ""
        for service in SERVICES:
            service_string += '<option value="%s">%s</option>' % (service, service)
        self.wfile.write(
            b"""
            <!DOCTYPE html>
            <html>
            <body>

            <h2>Service Form</h2>
            <p>tcp_client service will start a tcp client and connect to the given address and port.<\p>
            <form action="" method="post">
            <label for="service">Service:</label><br>
            <select id="service" name="service">
                %s
            </select><br>
            <label for="address">Address:</label><br>
            <input type="text" id="address" name="address" value=""><br>
            <label for="port">Port:</label><br>
            <input type="number" id="port" name="port"><br>
            <label for="message">Message:</label><br>
            <input type="text" id="message" name="message" value="Hello from flake!"><br>
            <label for="echo">Echo:</label>
            <input type="checkbox" id="echo" name="echo" value="1"><br><br>

            <input type="submit" value="Submit">
            </form>
            </body>
            </html>
            """
            % (service_string.encode("utf-8"))
        )

    def do_POST(self):
        """Start TCP client from request."""
        global DEFAULT_TIMEOUT, SERVICES, LOCAL_PORT_UDP
        bad_request_str = b"<html><body><h1>Bad Request!</h1></body></html>"
        try:
            form = cgi.FieldStorage(
                fp=self.rfile, headers=self.headers, environ={"REQUEST_METHOD": "POST"}
            )
            service = form.getvalue("service", None)
            if not service or service not in SERVICES:
                self._set_headers(400)
                self.wfile.write(bad_request_str)
                return

            request_vals = {
                "address": form.getvalue("address", None),
                "port": form.getvalue("port", None),
                "message": form.getvalue("message", "Hello from Flake Client!"),
                "echo": form.getvalue("echo", False),
            }
            flog.info(request_vals)
            if service in ["tcp_client", "udp_client"] and not (
                request_vals["address"]
                and request_vals["port"]
                and request_vals["port"].isdigit()
                and (request_vals["message"] or request_vals["echo"])
            ):
                self._set_headers(400)
                self.wfile.write(bad_request_str)
                return
            local_port = None
            if service == "udp_client":
                LOCAL_PORT_UDP += 1
                local_port = LOCAL_PORT_UDP
            if service in ["tcp_client", "udp_client"]:
                echo_client = EchoClient(
                    address=request_vals["address"],
                    port=int(request_vals["port"]),
                    message=request_vals["message"],
                    echo=request_vals["echo"],
                    mode="TCP" if service == "tcp_client" else "UDP",
                    local_port=local_port,
                    timeout=DEFAULT_TIMEOUT,
                )
                flog.info(f"Starting {service} thread.")
                _thread.start_new_thread(echo_client.run, ())
                self._set_headers(200)
                self.wfile.write(
                    b"<html><body><h1>Request Received, starting %s!</h1></body></html>"
                    % service.encode()
                )
        except Exception as e:
            self._set_headers(400)
            self.wfile.write(
                b"<html><body><h1>Bad Request!</h1><br><p>%s</p></body></html>"
                % repr(e).encode("utf-8")
            )


class HttpRequestServer:
    """Http request server class."""

    def __init__(self, config):
        """Initialize http server."""
        global DEFAULT_TIMEOUT
        self.config = config
        try:
            self.port = int(self.config["dynamic_http"]["port"])
        except (KeyError, ValueError) as e:
            flog.error("Could not get port for dynamic http server.")
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
    server = HttpRequestServer(config=config)
    server.run()


if __name__ == "__main__":
    main()
