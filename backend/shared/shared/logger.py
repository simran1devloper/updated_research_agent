"""
Centralized structured logger for all microservices.
Writes JSON lines to logs/app.log (rotating) + stdout.
Usage:
    from shared.logger import get_logger
    log = get_logger("research-service")
    log.info("msg", extra={"key": "val"})
"""
import logging
import logging.handlers
import json
import os
import sys
from datetime import datetime, timezone


class _JsonFormatter(logging.Formatter):
    """Emit one JSON object per log record."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": getattr(record, "service", record.name),
            "msg": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "line": record.lineno,
        }
        # Merge any extra fields passed via extra={...}
        for key, val in record.__dict__.items():
            if key not in logging.LogRecord.__dict__ and key not in payload:
                payload[key] = val
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def get_logger(service_name: str, log_dir: str = "logs") -> logging.Logger:
    """
    Return a logger configured with:
    - JSON rotating file handler  → logs/app.log  (10 MB × 5 backups)
    - Plain-text stream handler   → stdout
    Level is controlled by LOG_LEVEL env var (default INFO).
    """
    logger = logging.getLogger(service_name)
    if logger.handlers:
        return logger  # already configured

    level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
    logger.setLevel(level)

    os.makedirs(log_dir, exist_ok=True)

    # ── Rotating JSON file ──────────────────────────────────────────────────
    fh = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    fh.setFormatter(_JsonFormatter())
    fh.setLevel(level)

    # ── Stdout (human-readable) ─────────────────────────────────────────────
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    ))
    sh.setLevel(level)

    logger.addHandler(fh)
    logger.addHandler(sh)
    logger.propagate = False
    return logger
