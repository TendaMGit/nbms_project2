from collections import defaultdict
from threading import Lock

_COUNTERS = defaultdict(int)
_LOCK = Lock()


def _label_key(name, labels):
    if not labels:
        return (name, ())
    return (name, tuple(sorted(labels.items())))


def inc_counter(name, labels=None, value=1):
    key = _label_key(name, labels)
    with _LOCK:
        _COUNTERS[key] += value


def render_prometheus():
    lines = []
    for (name, labels), value in sorted(_COUNTERS.items(), key=lambda item: (item[0][0], item[0][1])):
        label_str = ""
        if labels:
            label_parts = [f'{k}="{v}"' for k, v in labels]
            label_str = "{" + ",".join(label_parts) + "}"
        lines.append(f"{name}{label_str} {value}")
    return "\n".join(lines) + "\n"
