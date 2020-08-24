import flog
import _thread
import os
import ssl
from socket import socket, AF_INET, SOCK_STREAM
from config_handler import ServerConfig


def tcp_tls_handle(conn_stream, client_sock):
    """Echo data over TLS connection."""
    flog.info("TCP TLS Handle Launched.")
    while True:
        try:
            data = conn_stream.read()
            if data:
                flog.debug("Received TCP TLS: {}".format(data))
                conn_stream.send(data)
            if not data:
                conn_stream.close()
                client_sock.close()
                break
        except ConnectionResetError:
            flog.info("TCP TLS Client Disconnected.")
            conn_stream.close()
            client_sock.close()
            break
        except socket.timeout as err:
            flog.info("TCP TLS Handler Timed Out. Closing Socket.")
            flog.info(err)
            conn_stream.close()
            client_sock.close()
            break
        except Exception as ex:
            flog.warning("TCP TLS Handler Exception: {}".format(ex))
            flog.info(ex)
            conn_stream.close()
            client_sock.close()
            break
    flog.info("End TCP TLS Handler.")


class TcpTLSServer:
    """TCP TLS server class."""

    def __init__(self, config):
        """Initialize tcp server."""
        self.config = config
        self.port = int(self.config["tcp_tls"]["port"])
        self.timeout = int(self.config["tcp_tls"]["timeout"])
        self.local_ip = "0.0.0.0"
        self.tcp_server = socket(AF_INET, SOCK_STREAM)
        self.fullchain = self.config["tcp_tls"]["fullchain"]
        self.privkey = self.config["tcp_tls"]["privkey"]

    def run(self):
        """Run TCP TLS server."""
        TLS_context = ssl.SSLContext(ssl.PROTOCOL_TLS)
        flog.debug("Loading cert and keyfile")
        TLS_context.load_cert_chain(certfile=self.fullchain, keyfile=self.privkey)

        self.tcp_server.bind((self.local_ip, self.port))
        self.tcp_server.listen(5)

        flog.debug("Starting TCP TLS server on {}".format(self.port))

        while True:
            # listen for tcp then wrap with TLS
            client_sock, addr = self.tcp_server.accept()
            client_sock.settimeout(self.timeout)
            flog.info("TCP Socket Connected.")
            try:
                conn_stream = TLS_context.wrap_socket(client_sock, server_side=True)
                _thread.start_new_thread(tcp_tls_handle, (conn_stream, client_sock))
            except Exception as ex:
                flog.info("Could not wrap socket. Closing TCP Socket.")
                flog.info(ex)
                client_sock.close()


def run_tcp_tls_server():
    """Run TCP TLS server."""
    flog.info("Starting TCP TLS echo server")
    config = ServerConfig()
    tcp_TLS_server = TcpTLSServer(config)
    tcp_TLS_server.run()

if __name__ == "__main__":
    run_tcp_tls_server()
