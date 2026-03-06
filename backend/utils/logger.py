# ==========================================
# utils/logger.py — Structured logging
# ==========================================

import logging
import os
from datetime import datetime

LOG_DIR  = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
LOG_FILE = os.path.join(LOG_DIR, f"astra_{datetime.now().strftime('%Y%m%d')}.log")

os.makedirs(LOG_DIR, exist_ok=True)

def setup_logger(name: str = "astra") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # File handler
    fh = logging.FileHandler(LOG_FILE)
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    ))

    logger.addHandler(fh)
    return logger
