"""Orren-generated input button watcher.
Target: input_button_watcher (Python)

Scoped responsibility: detect activation conditions
(double_click, volume_down x2) and emit activation signals.
"""

from __future__ import annotations

import time
from collections import deque


class InputButtonWatcher:
    """Detects double-click and volume-down-x2 sequences."""

    DOUBLE_CLICK_WINDOW_MS = 400
    VOLUME_DOWN_SEQUENCE = 2
    VOLUME_DOWN_WINDOW_MS = 800

    def __init__(self) -> None:
        self._click_times: deque = deque(maxlen=2)
        self._volume_down_times: deque = deque(maxlen=self.VOLUME_DOWN_SEQUENCE)
        self._activation_callbacks = []

    def on_activation(self, callback) -> None:
        self._activation_callbacks.append(callback)

    def _fire_activation(self, source: str) -> None:
        for cb in self._activation_callbacks:
            cb(source)

    def report_click(self) -> None:
        now_ms = time.time() * 1000
        self._click_times.append(now_ms)
        if len(self._click_times) == 2:
            if self._click_times[1] - self._click_times[0] <= self.DOUBLE_CLICK_WINDOW_MS:
                self._fire_activation("double_click")
                self._click_times.clear()

    def report_volume_down(self) -> None:
        now_ms = time.time() * 1000
        self._volume_down_times.append(now_ms)
        if len(self._volume_down_times) == self.VOLUME_DOWN_SEQUENCE:
            span = self._volume_down_times[-1] - self._volume_down_times[0]
            if span <= self.VOLUME_DOWN_WINDOW_MS:
                self._fire_activation("volume_down_x2")
                self._volume_down_times.clear()
