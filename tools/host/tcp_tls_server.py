import flog
import threading
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
        except Exception as ex:
            flog.warning("TCP TLS Handler Exception: {}".format(ex))
            conn_stream.close()
            client_sock.close()
            break
    flog.info("End TCP TLS Handler.")


class TcpTLSServer:
    """TCP TLS server class."""

    def __init__(self, config, mutual=False, ecdsa=False):
        """Initialize tcp server."""
        self.config = config
        self.is_mutual = mutual
        self.is_ecdsa = ecdsa
        self.timeout = int(self.config["tcp_tls"]["timeout"])
        self.local_ip = "0.0.0.0"
        self.tcp_server = socket(AF_INET, SOCK_STREAM)
        if self.is_ecdsa:
            self.timeout = int(self.config["ecdsa_tcp_tls"]["timeout"])
            self.fullchain = self.config["ecdsa_tcp_tls"]["fullchain"]
            self.privkey = self.config["ecdsa_tcp_tls"]["privkey"]
        else:
            self.timeout = int(self.config["tcp_tls"]["timeout"])
            self.fullchain = self.config["tcp_tls"]["fullchain"]
            self.privkey = self.config["tcp_tls"]["privkey"]
        flog.debug(f"[mutual={self.is_mutual}][ecdsa={self.is_ecdsa}] Server Config")
        if not self.is_mutual and not self.is_ecdsa:
            self.port = int(self.config["tcp_tls"]["port"])
        elif self.is_mutual and not self.is_ecdsa:
            self.port = int(self.config["tcp_tls_mutual"]["port"])
            self.CAroot = self.config["tcp_tls_mutual"]["CAroot"]
        elif not self.is_mutual and self.is_ecdsa:
            self.port = int(self.config["ecdsa_tcp_tls"]["port"])
        elif self.is_mutual and self.is_ecdsa:
            self.port = int(self.config["ecdsa_tcp_tls_mutual"]["port"])
            self.CAroot = self.config["ecdsa_tcp_tls_mutual"]["CAroot"]

    def run(self):
        """Run TCP TLS server."""
        TLS_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        flog.debug("Loading cert and keyfile")
        TLS_context.load_cert_chain(certfile=self.fullchain, keyfile=self.privkey)
        if self.is_mutual:
            flog.debug("Setting server to mutual authentication.")
            # CA root used for verifying Client certificates
            TLS_context.load_verify_locations(cafile=self.CAroot)
            TLS_context.verify_mode = ssl.CERT_REQUIRED

        self.tcp_server.bind((self.local_ip, self.port))
        self.tcp_server.listen(5)

        flog.debug("Starting TCP TLS server on {}".format(self.port))

        while True:
            # listen for tcp then wrap with TLS
            client_sock, client_address = self.tcp_server.accept()
            client_sock.settimeout(self.timeout)
            flog.info(f"TCP Socket Connected to {client_address}.")
            try:
                conn_stream = TLS_context.wrap_socket(client_sock, server_side=True)
                flog.debug(f"Connection cipher suite: {conn_stream.cipher()}")
                TLS_thread = threading.Thread(
                    target=tcp_tls_handle, args=(conn_stream, client_sock)
                )
                TLS_thread.start()
            except Exception as ex:
                flog.info("Could not wrap socket. Closing TCP Socket.")
                flog.info(ex)
            finally:
                client_sock.close()


def run_tcp_tls_server():
    """Run TCP TLS server."""
    flog.info("Starting TCP TLS echo server")
    config = ServerConfig()
    tcp_tls_server = TcpTLSServer(config)
    tcp_tls_server_mutual = TcpTLSServer(config, mutual=True)
    ecdsa_tcp_tls_server = TcpTLSServer(config, ecdsa=True)
    ecdsa_tcp_tls_server_mutual = TcpTLSServer(config, mutual=True, ecdsa=True)
    flog.debug("Launch tls tcp server thread.")
    tcp_tls_thread = threading.Thread(target=tcp_tls_server.run, args=())
    tcp_tls_thread.start()
    flog.debug("Launch tcp tls mutual authentication server thread.")
    tcp_tls_mutual_thread = threading.Thread(target=tcp_tls_server_mutual.run, args=())
    tcp_tls_mutual_thread.start()
    flog.debug("Launch ecdsa tcp tls server thread.")
    ecdsa_tcp_tls_thread = threading.Thread(target=ecdsa_tcp_tls_server.run, args=())
    ecdsa_tcp_tls_thread.start()
    flog.debug("Launch ecdsa tcp tls mutual authentication server thread.")
    ecdsa_tcp_tls_mutual_thread = threading.Thread(
        target=ecdsa_tcp_tls_server_mutual.run, args=()
    )
    ecdsa_tcp_tls_mutual_thread.start()
    tcp_tls_thread.join()
    tcp_tls_mutual_thread.join()
    ecdsa_tcp_tls_thread.join()
    ecdsa_tcp_tls_mutual_thread.join()


if __name__ == "__main__":
    run_tcp_tls_server()
