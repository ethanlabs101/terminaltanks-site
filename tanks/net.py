"""LAN networking: a newline-delimited JSON link over TCP, the host's UDP beacon, the lobby browser and a non-blocking
connector. (Not available in the browser.)"""
from __future__ import annotations

import json
import select
import socket
import time
from typing import Optional

from tanks import __version__
from tanks.config import BEACON_PORT, HUD_BOTTOM_ROWS, HUD_TOP_ROWS, LAN_PORT, MAX_FIELD_COLS, MAX_FIELD_ROWS


def field_size(cols: int, rows: int) -> tuple:
    """Battlefield pixel size a terminal of this size can show (what BattleScene would pick for itself)."""
    fc = min(cols, MAX_FIELD_COLS)
    fr = max(8, min(rows - HUD_TOP_ROWS - HUD_BOTTOM_ROWS, MAX_FIELD_ROWS))
    return fc, fr * 2


class NetLink:
    """One TCP connection speaking newline-delimited JSON, fully non-blocking (polled from the game loop)."""

    def __init__(self, sock: socket.socket) -> None:
        sock.setblocking(False)
        try:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except OSError:
            pass
        self.sock, self.rbuf, self.wbuf, self.inbox, self.dead = sock, b"", b"", [], False

    def send(self, obj: dict) -> None:
        if not self.dead:
            self.wbuf += (json.dumps(obj, separators=(",", ":")) + "\n").encode()
            self._flush()

    def _flush(self) -> None:
        while self.wbuf and not self.dead:
            try:
                n = self.sock.send(self.wbuf)
            except (BlockingIOError, InterruptedError):
                return
            except OSError:
                self.dead = True
                return
            self.wbuf = self.wbuf[n:]

    def pump(self) -> None:
        self._flush()
        while not self.dead:
            try:
                data = self.sock.recv(65536)
            except (BlockingIOError, InterruptedError):
                break
            except OSError:
                self.dead = True
                break
            if not data:
                self.dead = True
                break
            self.rbuf += data
        while b"\n" in self.rbuf:
            line, self.rbuf = self.rbuf.split(b"\n", 1)
            try:
                m = json.loads(line.decode("utf-8"))
            except ValueError:
                continue
            if isinstance(m, dict) and isinstance(m.get("t"), str):
                self.inbox.append(m)

    def take(self, *types: str) -> list:
        got = [m for m in self.inbox if m["t"] in types]
        if got:
            self.inbox = [m for m in self.inbox if m["t"] not in types]
        return got

    def peek(self, *types: str) -> Optional[dict]:
        return next((m for m in self.inbox if m["t"] in types), None)

    def drop(self, m: dict) -> None:
        for i, x in enumerate(self.inbox):
            if x is m:
                del self.inbox[i]
                return

    def close(self) -> None:
        try:
            self._flush()
            self.sock.close()
        except OSError:
            pass
        self.dead = True


WEB_LAN_TEXT = ("LAN play needs direct network access, which browsers do not allow, so it is disabled in the web version. "
                "Download the game to play LAN - the installed version works fully.")


def local_ips() -> list:
    ips: list = []
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))             # no packet is sent; it just asks the OS which interface would be used
        ips.append(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if ip not in ips and not ip.startswith("127."):
                ips.append(ip)
    except OSError:
        pass
    return ips or ["127.0.0.1"]


class LanHost:
    """Listens for one player and shouts 'game here' over UDP broadcast once a second so joiners can find it."""

    def __init__(self, name: str, port: int = LAN_PORT, beacon: bool = True, bind: str = "") -> None:
        self.name, self.t = name, 0.0
        self.srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        for p in ([port] if port == 0 else range(port, port + 10)):
            try:
                self.srv.bind((bind, p))
                break
            except OSError:
                continue
        else:
            raise OSError("no free LAN port")
        self.srv.listen(1)
        self.srv.setblocking(False)
        self.port = self.srv.getsockname()[1]
        self.udp: Optional[socket.socket] = None
        if beacon:
            try:
                self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            except OSError:
                self.udp = None

    def poll(self, dt: float) -> Optional[NetLink]:
        self.t -= dt
        if self.udp is not None and self.t <= 0:
            self.t = 1.0
            msg = json.dumps({"g": "TT", "name": self.name, "port": self.port, "ver": __version__}).encode()
            try:
                self.udp.sendto(msg, ("255.255.255.255", BEACON_PORT))
            except OSError:
                pass
        try:
            conn, _ = self.srv.accept()
        except (BlockingIOError, InterruptedError):
            return None
        except OSError:
            return None
        return NetLink(conn)

    def close(self) -> None:
        for s in (self.srv, self.udp):
            if s is not None:
                try:
                    s.close()
                except OSError:
                    pass


class LanBrowser:
    """Collects host beacons: {(ip, port): {'name', 'seen'}}."""

    def __init__(self, port: int = BEACON_PORT) -> None:
        self.hosts: dict = {}
        self.sock: Optional[socket.socket] = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, "SO_REUSEPORT"):
                try:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                except OSError:
                    pass
            s.bind(("", port))
            s.setblocking(False)
            self.sock = s
        except OSError:
            self.sock = None

    def poll(self) -> list:
        now = time.monotonic()
        while self.sock is not None:
            try:
                data, (ip, _) = self.sock.recvfrom(2048)
                m = json.loads(data.decode("utf-8"))
                if m.get("g") == "TT":
                    self.hosts[(ip, int(m["port"]))] = {"name": str(m.get("name", "HOST"))[:16], "seen": now}
            except (BlockingIOError, InterruptedError):
                break
            except (OSError, ValueError, KeyError, TypeError):
                break
        self.hosts = {k: v for k, v in self.hosts.items() if now - v["seen"] < 4.0}
        return sorted(self.hosts.items())

    def close(self) -> None:
        if self.sock is not None:
            self.sock.close()


class Connector:
    """Non-blocking TCP connect (so the menu never freezes while a host is unreachable)."""

    def __init__(self, host: str, port: int, timeout: float = 6.0) -> None:
        self.error, self.t0, self.timeout = "", time.monotonic(), timeout
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setblocking(False)
        try:
            self.sock.connect_ex((host, port))
        except (OSError, UnicodeError) as e:
            self.error = str(e) or "bad address"

    def poll(self) -> Optional[NetLink]:
        if self.error:
            return None
        if time.monotonic() - self.t0 > self.timeout:
            self.error = "timed out"
            return None
        try:
            _, w, x = select.select([], [self.sock], [self.sock], 0)
        except (OSError, ValueError) as e:
            self.error = str(e)
            return None
        if w or x:
            err = self.sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            if err or x and not w:
                self.error = "connection refused" if err else "failed"
                return None
            return NetLink(self.sock)
        return None
