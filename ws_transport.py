"""A small, standard-library WebSocket server (RFC 6455) used for local development and tests.

In production the same duel logic is served on the app's own port through flask-sock (see server.py). This transport exists so
`python server.py` also works for live duels when flask-sock is not installed. It listens on PORT+1 and only accepts text frames.
"""
import base64
import hashlib
import select
import socket
import socketserver
import struct
import threading
from urllib.parse import parse_qs, urlsplit

import duel

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
MAX_FRAME = 64 * 1024


class ConnectionClosed(Exception):
    pass


class MiniWS:
    """Server side of one WebSocket connection, with the same small interface flask-sock gives us."""

    def __init__(self, sock):
        self.sock, self.lock, self.open = sock, threading.Lock(), True

    def _read(self, n):
        data = b""
        while len(data) < n:
            chunk = self.sock.recv(n - len(data))
            if not chunk:
                raise ConnectionClosed()
            data += chunk
        return data

    def _frame(self, opcode, payload=b""):
        n = len(payload)
        head = bytes([0x80 | opcode]) + (bytes([n]) if n < 126 else b"\x7e" + struct.pack("!H", n) if n < 65536 else b"\x7f" + struct.pack("!Q", n))
        with self.lock:
            self.sock.sendall(head + payload)

    def send(self, text):
        if not self.open:
            raise ConnectionClosed()
        try:
            self._frame(0x1, text.encode("utf-8"))
        except OSError:
            self.open = False
            raise ConnectionClosed()

    def receive(self, timeout=None):
        """Returns the next text message, or None if nothing arrived within timeout seconds."""
        message = b""
        while True:
            if not message:
                ready, _, _ = select.select([self.sock], [], [], timeout)
                if not ready:
                    return None
            self.sock.settimeout(10)
            try:
                b1, b2 = self._read(2)
                opcode, fin, masked, ln = b1 & 0x0F, b1 & 0x80, b2 & 0x80, b2 & 0x7F
                if ln == 126:
                    ln = struct.unpack("!H", self._read(2))[0]
                elif ln == 127:
                    ln = struct.unpack("!Q", self._read(8))[0]
                if ln > MAX_FRAME or not masked:
                    self.close()
                    raise ConnectionClosed()
                key = self._read(4)
                payload = bytes(b ^ key[i % 4] for i, b in enumerate(self._read(ln)))
            except (OSError, socket.timeout):
                self.open = False
                raise ConnectionClosed()
            if opcode == 0x8:
                self.close()
                raise ConnectionClosed()
            if opcode == 0x9:
                self._frame(0xA, payload)
                continue
            if opcode in (0x1, 0x0):
                message += payload
                if fin:
                    return message.decode("utf-8", "replace")
            # binary and pong frames are ignored

    def close(self):
        if self.open:
            self.open = False
            try:
                self._frame(0x8, b"")
            except OSError:
                pass
        try:
            self.sock.close()
        except OSError:
            pass


class _Handler(socketserver.BaseRequestHandler):
    def _reject(self, code, reason):
        try:
            self.request.sendall(("HTTP/1.1 %d %s\r\nConnection: close\r\nContent-Length: 0\r\n\r\n" % (code, reason)).encode())
        except OSError:
            pass

    def handle(self):
        sock = self.request
        sock.settimeout(5)
        raw = b""
        try:
            while b"\r\n\r\n" not in raw and len(raw) < 8192:
                chunk = sock.recv(2048)
                if not chunk:
                    return
                raw += chunk
        except OSError:
            return
        lines = raw.decode("latin-1").split("\r\n")
        try:
            method, target, _ = lines[0].split(" ", 2)
        except ValueError:
            return self._reject(400, "Bad Request")
        headers = {}
        for ln in lines[1:]:
            if ":" in ln:
                k, v = ln.split(":", 1)
                headers[k.strip().lower()] = v.strip()
        if method != "GET" or headers.get("upgrade", "").lower() != "websocket" or "sec-websocket-key" not in headers:
            return self._reject(400, "Bad Request")
        origin = headers.get("origin")
        if origin and urlsplit(origin).hostname != (headers.get("host", "").split(":")[0]):
            return self._reject(403, "Forbidden")  # only pages served from this host may connect
        url = urlsplit(target)
        parts = url.path.strip("/").split("/")
        if len(parts) != 3 or parts[0] != "ws" or parts[1] != "duel":
            return self._reject(404, "Not Found")
        accept = base64.b64encode(hashlib.sha1((headers["sec-websocket-key"] + GUID).encode()).digest()).decode()
        sock.sendall(("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: %s\r\n\r\n" % accept).encode())
        name = (parse_qs(url.query).get("name") or [""])[0]
        duel.serve(MiniWS(sock), parts[2], name)


class _Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def start(port):
    """Start the development WebSocket server on a background thread. Returns the server."""
    srv = _Server(("0.0.0.0", port), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
