from urllib.parse import quote

from .base import Arch, Res


class Arc(Arch):
    name = "archive_today"

    def submit(self, url: str) -> Res:
        archive_url = (
            "https://archive.today/?run=1&url="
            + quote(url, safe="")
        )

        return Res(
            ok=False,
            url=archive_url,
            err="manual_required",
        )

    def status(self, aid: str) -> dict:
        return {}
