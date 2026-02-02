"""
Centralized logging configuration for the application.
Logs to both console and a rotating file (logs/app.log).
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_FILE = LOG_DIR / "app.log"
MAX_BYTES = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 5

FORMAT_CONSOLE = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
FORMAT_FILE = "%(asctime)s | %(levelname)-7s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
DATE_FMT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: str = "INFO") -> None:
    """Configure root logger with console and rotating file handlers."""
    level_value = getattr(logging, level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(level_value)

    # Avoid duplicate handlers when reloading
    if root.handlers:
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    fmt_console = logging.Formatter(FORMAT_CONSOLE, datefmt=DATE_FMT)
    fmt_file = logging.Formatter(FORMAT_FILE, datefmt=DATE_FMT)

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level_value)
    console.setFormatter(fmt_console)
    root.addHandler(console)

    try:
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(level_value)
        file_handler.setFormatter(fmt_file)
        root.addHandler(file_handler)
    except OSError:
        root.warning("Could not create log file %s; file logging disabled", LOG_FILE)

    # Reduce noise from third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
