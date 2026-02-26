import json
import logging

from nbms_app.logging_utils import JsonLogFormatter, RequestIdLogFilter, SensitiveDataFilter
from nbms_app.services.request_id import set_current_request_id, reset_current_request_id


def test_json_log_formatter_includes_request_metadata():
    record = logging.LogRecord(
        name="nbms.request",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="request.completed",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-123"
    record.user_id = 77
    record.method = "GET"
    record.path = "/healthz/"
    record.status_code = 200
    record.latency_ms = 8.25

    formatter = JsonLogFormatter()
    payload = json.loads(formatter.format(record))

    assert payload["request_id"] == "req-123"
    assert payload["user_id"] == 77
    assert payload["method"] == "GET"
    assert payload["path"] == "/healthz/"
    assert payload["status_code"] == 200
    assert payload["latency_ms"] == 8.25


def test_request_id_filter_sets_defaults_and_context_request_id():
    token = set_current_request_id("req-context-1")
    try:
        record = logging.LogRecord(
            name="nbms.request",
            level=logging.INFO,
            pathname=__file__,
            lineno=42,
            msg="message",
            args=(),
            exc_info=None,
        )
        RequestIdLogFilter().filter(record)

        assert record.request_id == "req-context-1"
        assert record.user_id == "-"
        assert record.method == "-"
        assert record.path == "-"
        assert record.status_code == "-"
        assert record.latency_ms == "-"
    finally:
        reset_current_request_id(token)


def test_sensitive_data_filter_redacts_passwords_and_tokens():
    record = logging.LogRecord(
        name="nbms.request",
        level=logging.INFO,
        pathname=__file__,
        lineno=70,
        msg="login failed password=hunter2 token=abc123",
        args=(),
        exc_info=None,
    )

    SensitiveDataFilter().filter(record)

    assert "hunter2" not in record.msg
    assert "abc123" not in record.msg
    assert "password=[REDACTED]" in record.msg
    assert "token=[REDACTED]" in record.msg
