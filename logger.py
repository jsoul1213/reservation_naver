"""Logging setup shared by the GUI and background monitor."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from queue import Queue

from config import DEFAULT_LOG_PATH


class GuiQueueHandler(logging.Handler):
    def __init__(self, output: Queue[str]) -> None:
        super().__init__()
        self.output = output

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.output.put_nowait(self.format(record))
        except Exception:
            self.handleError(record)


def setup_logging(
    gui_queue: Queue[str] | None = None,
    log_path: Path = DEFAULT_LOG_PATH,
) -> logging.Logger:
    logger = logging.getLogger("reservation_monitor")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.handlers.clear()

    formatter = logging.Formatter("[%(asctime)s] %(levelname)s %(message)s", "%H:%M:%S")
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_path, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        # The program can still run if its log folder is temporarily unavailable.
        pass

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if gui_queue is not None:
        gui_handler = GuiQueueHandler(gui_queue)
        gui_handler.setFormatter(formatter)
        logger.addHandler(gui_handler)

    return logger
