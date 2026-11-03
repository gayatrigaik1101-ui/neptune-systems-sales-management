"""
Neptune Systems - Sales Management System
Utility Functions & Logging Setup
"""

import logging
from logging.handlers import RotatingFileHandler
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from app.config import LOGS_DIR

# Configure rotating application logger
APP_LOG_PATH = LOGS_DIR / "app.log"
AUDIT_LOG_PATH = LOGS_DIR / "audit.log"

def setup_logger(name: str = "neptune_sales", log_file: Path = APP_LOG_PATH, level: int = logging.INFO) -> logging.Logger:
    """Configures and returns a logger instance with console and file handlers."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level)

        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # File handler (10 MB max, 5 backups)
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)
        logger.addHandler(console_handler)

    return logger

logger = setup_logger("neptune_app", APP_LOG_PATH)
audit_sys_logger = setup_logger("neptune_audit_sys", AUDIT_LOG_PATH)


def get_current_timestamp_str(format_str: str = "%d-%m-%Y %H:%M:%S") -> str:
    """Returns formatted current timestamp string."""
    return datetime.now().strftime(format_str)


def get_current_date_str(format_str: str = "%d-%m-%Y") -> str:
    """Returns formatted current date string."""
    return datetime.now().strftime(format_str)


def parse_date_string(date_str: str) -> Optional[datetime]:
    """Attempts to parse common date formats into datetime object."""
    if not date_str:
        return None
    date_str = str(date_str).strip()
    formats = [
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%d-%m-%Y %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%m/%d/%Y"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def generate_entry_id(prefix: str = "NEP") -> str:
    """Generates a unique business Entry ID (e.g. NEP-20261102-A1B2)."""
    date_part = datetime.now().strftime("%Y%m%d")
    unique_suffix = uuid.uuid4().hex[:4].upper()
    return f"{prefix}-{date_part}-{unique_suffix}"


def generate_history_id() -> str:
    """Generates a unique audit History ID (e.g. HIST-20261102-124500-F1A2)."""
    ts_part = datetime.now().strftime("%Y%m%d-%H%M%S")
    rand_suffix = uuid.uuid4().hex[:4].upper()
    return f"HIST-{ts_part}-{rand_suffix}"


def clean_string(val: Any) -> str:
    """Strips whitespace and converts None/NaN to empty string."""
    if val is None:
        return ""
    s = str(val).strip()
    if s.lower() in ("nan", "none", "null"):
        return ""
    return s


def sanitize_phone_number(phone: Any) -> str:
    """Extracts only numeric digits from phone string."""
    if phone is None:
        return ""
    digits = re.sub(r"\D", "", str(phone).strip())
    # Strip leading country code 91 if length is 12 and starts with 91
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    return digits
