import threading
import uuid
import logging

_local = threading.local()

def set_request_id(rid: str = None) -> str:
    _local.request_id = rid or uuid.uuid4().hex[:8]
    return _local.request_id

def get_request_id() -> str:
    return getattr(_local, "request_id", "-")

def clear_request_id():
    _local.request_id = "-"

class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = get_request_id()
        try:
            from utils.telemetry import get_current_trace_id
            record.trace_id = get_current_trace_id()
        except Exception:
            record.trace_id = "-"
        return True

def init_request_id_logging():
    f = RequestIdFilter()
    root = logging.getLogger()
    if not any(isinstance(x, RequestIdFilter) for x in root.filters):
        root.addFilter(f)
