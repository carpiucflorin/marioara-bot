from __future__ import annotations

import queue
import threading
import logging
from typing import Any, Callable


class BackgroundWorker:
    def __init__(self):
        self._queue = queue.PriorityQueue()
        self._stop = threading.Event()
        self.errors = []
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def enqueue(self, task: Callable[[], Any], priority: int = 5) -> None:
        self._queue.put((priority, id(task), task))

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                _, _, task = self._queue.get(timeout=0.2)
                try:
                    task()
                except Exception as error:
                    self.errors.append(error)
                    logging.exception("Background task failed")
                finally:
                    self._queue.task_done()
            except queue.Empty:
                continue

    def stop(self) -> None:
        self._stop.set()
