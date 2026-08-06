from __future__ import annotations

import threading
import time


class AppState:
    """Estado compartilhado com segurança entre MAVLink e servidor web."""

    def __init__(self, title: str, display_type: str = "LCD") -> None:
        self._lock = threading.Lock()
        self.depth_m: float | None = None
        self.source: str | None = None
        self.last_update: float | None = None
        self.mavlink_connected = False
        self.display_connected = False
        self.display_error: str | None = None
        self.display_type = display_type
        self.title = title[:16]
        self.test_requested = False

    def update_depth(self, depth_m: float, source: str) -> None:
        with self._lock:
            self.depth_m = depth_m
            self.source = source
            self.last_update = time.time()
            self.mavlink_connected = True

    def set_mavlink_disconnected(self) -> None:
        with self._lock:
            self.mavlink_connected = False

    def set_display_status(self, connected: bool, error: str | None = None) -> None:
        with self._lock:
            self.display_connected = connected
            self.display_error = error

    def set_title(self, title: str) -> None:
        with self._lock:
            self.title = title[:16]

    def request_test(self) -> None:
        with self._lock:
            self.test_requested = True

    def consume_test_request(self) -> bool:
        with self._lock:
            requested = self.test_requested
            self.test_requested = False
            return requested

    def snapshot(self) -> dict:
        with self._lock:
            age = None if self.last_update is None else time.time() - self.last_update
            return {
                "depth_m": self.depth_m,
                "source": self.source,
                "last_update": self.last_update,
                "age_seconds": age,
                "mavlink_connected": self.mavlink_connected,
                "display_connected": self.display_connected,
                "display_error": self.display_error,
                "display_type": self.display_type,
                "title": self.title,
            }
