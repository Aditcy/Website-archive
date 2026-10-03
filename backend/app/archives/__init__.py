from .wayback import Way
from .archive_today import Arc


def get(name):
    return {
        "wayback": Way(),
        "archive_today": Arc(),
    }.get(name)
