from .wayback import Way
from .archive_today import Arc


def get(name: str):
    providers = {
        "wayback": Way(),
        "archive_today": Arc(),
    }

    return providers.get(name.strip().lower())
