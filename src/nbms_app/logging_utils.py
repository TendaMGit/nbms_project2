import json
import logging
import re
from datetime import datetime, timezone

from nbms_app.services.request_id import get_current_request_id

_SENSITIVE_PATTERN = re.compile(
    r"(?i)\b(password|pass|token|authorization|secret|api[_-]?key|jwt)\b\s*[:=]\s*[^,\s;]+"
)
_REDACTED = "[REDACTED]"


class RequestIdLogFilter(logging.Filter):
    def filter(self, record):
        record.request_id = getattr(record, "request_id", get_current_request_id())
        record.user_id = getattr(record, "user_id", "-")
        record.method = getattr(record, "method", "-")
        record.path = getattr(record, "path", "-")
        record.status_code = getattr(record, "status_code", "-")
        record.latency_ms = getattr(record, "latency_ms", "-")
        return True


class JsonLogFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", get_current_request_id()),
            "user_id": getattr(record, "user_id", None),
            "method": getattr(record, "method", None),
            "path": getattr(record, "path", None),
            "status_code": getattr(record, "status_code", None),
            "latency_ms": getattr(record, "latency_ms", None),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, sort_keys=True, default=str)


class SensitiveDataFilter(logging.Filter):
    """Redact common secret-like values before logs are emitted."""

    redacted_fields = (
        "password",
        "pass",
        "token",
        "authorization",
        "secret",
        "api_key",
        "api-token",
        "jwt",
    )

    def filter(self, record):
        message = record.getMessage()
        sanitized_message = _SENSITIVE_PATTERN.sub(lambda m: f"{m.group(1)}={_REDACTED}", message)
        if sanitized_message != message:
            record.msg = sanitized_message
            record.args = ()

        for field_name in self.redacted_fields:
            if hasattr(record, field_name):
                setattr(record, field_name, _REDACTED)
        return True
