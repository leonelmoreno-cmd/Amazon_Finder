# utils/logging_setup.py
from __future__ import annotations
import logging
from typing import List

class InMemoryLogHandler(logging.Handler):
    """Collect log records in memory for UI display."""
    def __init__(self, capacity: int = 500):
        super().__init__()
        self.capacity = capacity
        self.records: List[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        self.records.append(msg)
        if len(self.records) > self.capacity:
            self.records.pop(0)

def setup_logging(level: int = logging.INFO) -> InMemoryLogHandler:
    logger = logging.getLogger()
    logger.setLevel(level)
    # Avoid duplicate handlers during hot-reload
    for h in list(logger.handlers):
        logger.removeHandler(h)

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)s - %(name)s - %(message)s",
        datefmt="%H:%M:%S"
    )

    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(fmt)
    logger.addHandler(console)

    mem = InMemoryLogHandler()
    mem.setLevel(level)
    mem.setFormatter(fmt)
    logger.addHandler(mem)

    return mem
