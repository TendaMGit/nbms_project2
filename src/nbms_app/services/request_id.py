from contextvars import ContextVar


_current_request_id = ContextVar("current_request_id", default="-")


def set_current_request_id(request_id):
    return _current_request_id.set(request_id or "-")


def reset_current_request_id(token):
    if token is not None:
        _current_request_id.reset(token)


def get_current_request_id():
    return _current_request_id.get()
