from contextvars import ContextVar

_current_request = ContextVar("current_request", default=None)


def set_current_request(request):
    return _current_request.set(request)


def reset_current_request(token):
    if token is not None:
        _current_request.reset(token)


def get_current_request():
    return _current_request.get()
