"""
TSDBServer — a runnable TCP server for the database
===================================================

Wraps the framing + protocol + validation + execution layers into a real server that
listens on a port and serves many clients, each backed by a shared ``TimeSeriesDB``.

Run it:
    python -m tsdb --host 127.0.0.1 --port 8080 --data ./data

Talk to it with the built-in client:
    from tsdb.server import Client
    import socket
    c = Client(socket.create_connection(("127.0.0.1", 8080)))
    c.ping()
    c.write("cpu", {"host": "s1"}, {"usage": 75.5})
    c.query("SELECT mean(usage) FROM cpu")
"""

from __future__ import annotations

import socket
import threading
from typing import Optional

from .database import TimeSeriesDB
from .server.query_parser import ParseError
from .server.error_handling import handle_request, QueryError
from .server.tcp_server import serve_connection


class TSDBServer:
    """A threaded TCP server exposing a TimeSeriesDB over the TSDB wire protocol."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8080, data_path: str = "data"):
        self.host = host
        self.port = port
        self.db = TimeSeriesDB(data_path)
        self._sock: Optional[socket.socket] = None
        self._threads: list[threading.Thread] = []
        self._running = False

    # ---- request handling -------------------------------------------------
    def _handler(self, request: bytes) -> bytes:
        """bytes-in / bytes-out: decode the request, route it, encode the response."""
        text = request.decode("utf-8")

        def write_handler(measurement, tags, fields, ts):
            self.db.write(measurement, tags, fields, timestamp=ts)

        def query_handler(q):
            try:
                return self.db.query(q)
            except ParseError as e:  # bad SQL is the client's fault -> 422, not 500
                raise QueryError(f"parse error: {e}")

        response = handle_request(text, write_handler, query_handler)
        return response.encode("utf-8")

    # ---- lifecycle --------------------------------------------------------
    def serve_forever(self) -> None:
        """Bind, listen, and accept connections until stop() is called."""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self._sock.listen(128)
        # If port was 0, discover the OS-assigned one.
        self.port = self._sock.getsockname()[1]
        self._running = True
        print(f"tsdb: listening on {self.host}:{self.port} (data → {self.db._storage.base_path})")

        try:
            while self._running:
                try:
                    conn, _ = self._sock.accept()
                except OSError:
                    break  # socket closed by stop()
                t = threading.Thread(target=self._serve_conn, args=(conn,), daemon=True)
                t.start()
                self._threads.append(t)
        finally:
            self.stop()

    def _serve_conn(self, conn: socket.socket) -> None:
        with conn:
            try:
                serve_connection(conn, self._handler)
            except (ConnectionError, OSError):
                pass  # client disconnected mid-stream

    def stop(self) -> None:
        """Stop accepting, close the socket, and shut the database down cleanly."""
        self._running = False
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        try:
            self.db.close()
        except Exception:
            pass


def main(argv: Optional[list] = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(prog="python -m tsdb", description="Run the TSDB TCP server.")
    parser.add_argument("--host", default="127.0.0.1", help="bind host (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="bind port (default 8080; 0 = auto)")
    parser.add_argument("--data", default="data", help="storage directory (default ./data)")
    args = parser.parse_args(argv)

    server = TSDBServer(host=args.host, port=args.port, data_path=args.data)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\ntsdb: shutting down")
        server.stop()


if __name__ == "__main__":
    main()
