import logging
import json
import os
from datetime import datetime, timezone, timezone

LOG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs"
)
os.makedirs(LOG_DIR, exist_ok=True)

AGENT_LOG = os.path.join(LOG_DIR, "agent.log")
SYSTEM_LOG = os.path.join(LOG_DIR, "system.log")
CHAT_LOG = os.path.join(LOG_DIR, "chat.log")


class JSONFormatter(logging.Formatter):
    def format(self, record):
        log = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "trace_id": getattr(record, "trace_id", "-"),
            "msg": record.getMessage(),
        }
        if hasattr(record, "event"):
            log["event"] = record.event
        if hasattr(record, "data"):
            log["data"] = record.data
        return json.dumps(log)


def _make_logger(name: str, filepath: str, level=logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        fh = logging.FileHandler(filepath)
        fh.setFormatter(JSONFormatter())
        logger.addHandler(fh)
        # Also print to console in human-readable form
        ch = logging.StreamHandler()
        ch.setFormatter(
            logging.Formatter(
                "\x1b[36m%(asctime)s\x1b[0m \x1b[33m[%(name)s]\x1b[0m %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        ch.setLevel(level)
        logger.addHandler(ch)
    return logger


# Three named loggers — import these directly
agent_logger = _make_logger("astra.agent", AGENT_LOG)
system_logger = _make_logger("astra.system", SYSTEM_LOG)
chat_logger = _make_logger("astra.chat", CHAT_LOG)


def log_event(logger: logging.Logger, event: str, **data):
    """
    Structured log helper.
    Usage: log_event(agent_logger, "react_step", step=1, action="web_search")
    """
    record = logging.LogRecord(
        name=logger.name,
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg=f"{event} | {data}",
        args=(),
        exc_info=None,
    )
    record.event = event
    record.data = data
    logger.handle(record)
