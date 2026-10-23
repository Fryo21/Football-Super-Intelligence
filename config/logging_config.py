
"""Central logging configuration for FSI."""

import logging
import os
import time
from logging.handlers import RotatingFileHandler

from config.paths import LOG_DIR


def configure_logging() -> None:
    """Configure console and rotating file logging once."""

    logger = logging.getLogger("fsi")

    if logger.handlers:
        return

    level_name = os.getenv("FSI_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, None)

    if not isinstance(level, int):
        raise ValueError(f"Invalid FSI_LOG_LEVEL: {level_name}")

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | "
        "%(name)s | %(message)s"
    )
    formatter.converter = time.gmtime

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        LOG_DIR / "fsi.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logger.setLevel(level)
    logger.addHandler(console)
    logger.addHandler(file_handler)
    logger.propagate = False
