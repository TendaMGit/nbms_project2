import json
import logging
from datetime import datetime, timezone

from nbms_app.services.request_id import get_current_request_id


class RequestIdLogFilter(logging.Filter):
    def filter(self, record):
        record.request_id = getattr(record, "request_id", get_current_request_id())
        return True


class JsonLogFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", get_current_request_id()),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, sort_keys=True, default=str)
