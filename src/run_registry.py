"""Active run registry for cancellation support."""

from __future__ import annotations

import threading

_active_runs: dict[str, object] = {}
_lock = threading.Lock()


def register_run(run_id: str, callback_handler: object) -> None:
    with _lock:
        _active_runs[run_id] = callback_handler


def unregister_run(run_id: str) -> None:
    with _lock:
        _active_runs.pop(run_id, None)


def get_run_handler(run_id: str) -> object | None:
    with _lock:
        return _active_runs.get(run_id)
