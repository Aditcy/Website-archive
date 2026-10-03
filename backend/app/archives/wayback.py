import time
import httpx
from urllib.parse import quote

from ..config import cfg
from .base import Arch, Res


class Way(Arch):
    name = "wayback"

    def submit(self, url):
        h = {
            "Accept": "application/json",
            "User-Agent": cfg.user_agent,
        }

        if not cfg.ia_key or not cfg.ia_secret:
            try:
                r = httpx.get(
                    "https://web.archive.org/save/"
                    + quote(url, safe=":/?=&%"),
                    headers=h,
                    timeout=60,
                    follow_redirects=False,
                )

                if r.status_code == 401:
                    return Res(
                        False,
                        err="auth_required: Wayback requires IA_KEY/IA_SECRET",
                    )

                loc = (
                    r.headers.get("location")
                    or r.headers.get("content-location")
                )

                if loc:
                    return Res(True, loc)

                if r.status_code >= 400:
                    return Res(
                        False,
                        err=f"HTTP {r.status_code}: {r.text[:500]}",
                    )

                return Res(
                    False,
                    err="No archive location returned",
                )

            except Exception as e:
                return Res(False, err=str(e)[:1000])

        h["Authorization"] = f"LOW {cfg.ia_key}:{cfg.ia_secret}"

        try:
            r = httpx.post(
                "https://web.archive.org/save",
                headers=h,
                data={
                    "url": url,
                    "skip_first_archive": "1",
                },
                timeout=60,
            )

            if r.status_code == 401:
                return Res(
                    False,
                    err="auth_required: Wayback credentials rejected",
                )

            if r.status_code >= 400:
                return Res(
                    False,
                    err=f"HTTP {r.status_code}: {r.text[:500]}",
                )

            j = r.json()
            aid = j.get("job_id")

            if not aid:
                return Res(False, err="No job_id returned")

            for _ in range(24):
                s = httpx.get(
                    f"https://web.archive.org/save/status/{aid}",
                    headers=h,
                    timeout=30,
                )

                if s.status_code == 401:
                    return Res(
                        False,
                        aid=aid,
                        err="auth_required: Wayback credentials rejected",
                    )

                z = s.json()

                if z.get("status") == "success":
                    ts = z.get("timestamp")
                    original = z.get("original_url") or url

                    return Res(
                        True,
                        f"https://web.archive.org/web/{ts}/{original}",
                        aid,
                    )

                if z.get("status") == "error":
                    return Res(
                        False,
                        aid=aid,
                        err=(
                            z.get("message")
                            or z.get("status_ext")
                            or "capture failed"
                        ),
                    )

                time.sleep(5)

            return Res(
                False,
                aid=aid,
                err="capture pending after timeout",
            )

        except Exception as e:
            return Res(False, err=str(e)[:1000])

    def status(self, aid):
        try:
            return httpx.get(
                f"https://web.archive.org/save/status/{aid}",
                timeout=30,
            ).json()
        except Exception:
            return {}
