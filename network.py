"""
BLACKFROS - network
v3.0.0-pre.1
"""

import socket
import sys

DEFAULT_PORT = 5050
DEFAULT_TOR_PROXY_HOST = "127.0.0.1"
DEFAULT_TOR_PROXY_PORT = 9050


def make_raw_socket(use_tor, proxy_host, proxy_port):

    if not use_tor:
        return socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        import socks
    except ImportError:
        print("Falta 'pysocks'. Instalalo con: pip install pysocks")
        sys.exit(1)

    s = socks.socksocket(socket.AF_INET, socket.SOCK_STREAM)
    s.set_proxy(socks.SOCKS5, proxy_host, proxy_port, rdns=True)
    return s


class Connection:

    def __init__(self, ip, port, use_tor=False,
                 proxy_host=DEFAULT_TOR_PROXY_HOST, proxy_port=DEFAULT_TOR_PROXY_PORT):
        self.ip = ip
        self.port = port
        self.use_tor = use_tor
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.sock = None
        self._buf = None

    def connect(self, nickname):
        self.sock = make_raw_socket(self.use_tor, self.proxy_host, self.proxy_port)
        self.sock.connect((self.ip, self.port))
        self.sock.sendall((nickname + "\n").encode("utf-8"))
        self._buf = self.sock.makefile("r", encoding="utf-8")

    def send(self, text):
        if not text or not self.sock:
            return
        self.sock.sendall((text + "\n").encode("utf-8"))

    def lines(self):
        try:
            for line in self._buf:
                line = line.rstrip("\n")
                if line:
                    yield line
        except OSError:
            return

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass


def classify(line):
    if line.startswith("OK"):
        return "ok"
    if line.startswith("ERROR"):
        return "error"
    if line.startswith("CHAT ") or line.startswith("DM "):
        return "chat"
    if line.startswith("*"):
        return "event"
    return "dim"