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

    def __init__(self, config, mutual=False):
        """Initialize tcp server."""
        self.config = config
        self.timeout = int(self.config["tcp_tls"]["timeout"])
        self.local_ip = "0.0.0.0"
        self.tcp_server = socket(AF_INET, SOCK_STREAM)
        self.fullchain = self.config["tcp_tls"]["fullchain"]
        self.privkey = self.config["tcp_tls"]["privkey"]
        self.is_mutual = mutual
        if self.is_mutual is False:
            self.port = int(self.config["tcp_tls"]["port"])
        else:
            self.port = int(self.config["tcp_tls_mutual"]["port"])
            self.CAroot = self.config["tcp_tls_mutual"]["CAroot"]

    def run(self):
        """Run TCP TLS server."""
        TLS_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        flog.debug("Loading cert and keyfile")
        TLS_context.load_cert_chain(certfile=self.fullchain, keyfile=self.privkey)
        if self.is_mutual is True:
            flog.debug("Setting server to mutual authentication.")
            # CA root used for verifying Client certificates
            TLS_context.load_verify_locations(cafile=self.CAroot)
            TLS_context.verify_mode = ssl.CERT_REQUIRED

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
                TLS_thread = threading.Thread(
                    target=tcp_tls_handle, args=(conn_stream, client_sock)
                )
                TLS_thread.start()
            except Exception as ex:
                flog.info("Could not wrap socket. Closing TCP Socket.")
                flog.info(ex)
                client_sock.close()


def run_tcp_tls_server():
    """Run TCP TLS server."""
    flog.info("Starting TCP TLS echo server")
    config = ServerConfig()
    tcp_TLS_server = TcpTLSServer(config)
    tcp_TLS_server_mutual = TcpTLSServer(config, mutual=True)

    flog.debug("Launch mutual authentication server thread.")
    mutual_thread = threading.Thread(target=tcp_TLS_server_mutual.run, args=())
    mutual_thread.start()
    flog.debug("Launch server authentication server thread.")
    server_thread = threading.Thread(target=tcp_TLS_server.run, args=())
    server_thread.start()
    mutual_thread.join()
    server_thread.join()


if __name__ == "__main__":
    run_tcp_tls_server()
