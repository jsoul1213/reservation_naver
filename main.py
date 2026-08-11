"""Reservation Monitor desktop entry point."""

from __future__ import annotations

import os
import queue
import sys
import tkinter as tk
from tkinter import messagebox

from gui import ReservationMonitorGUI
from logger import setup_logging


def main() -> int:
    # The macOS build script embeds Chromium under the Playwright package.
    if getattr(sys, "frozen", False):
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "0")

    log_queue: queue.Queue[str] = queue.Queue()
    logger = setup_logging(log_queue)
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        logger.exception("GUI could not be started")
        return 1
    try:
        ReservationMonitorGUI(root, logger, log_queue)
        root.mainloop()
    except Exception as exc:
        logger.exception("Unhandled GUI error")
        try:
            messagebox.showerror("Reservation Monitor", str(exc))
        except Exception:
            pass
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
