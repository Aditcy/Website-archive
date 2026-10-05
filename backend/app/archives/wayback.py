import time
import httpx
from urllib.parse import quote

from ..config import cfg
from .base import Arch, Res


class Way(Arch):
    name = "wayback"

    save_url = "https://web.archive.org/save"
    save_get_url = "https://web.archive.org/save/"

    def submit(self, url):
        headers = {
            "Accept": "application/json",
            "User-Agent": cfg.user_agent,
        }

        if not cfg.ia_key or not cfg.ia_secret:
            return self._submit_public(url, headers)

        return self._submit_authenticated(url, headers)

    def _submit_public(self, url, headers):
        try:
            response = httpx.get(
                self.save_get_url + quote(url, safe=":/?=&%"),
                headers=headers,
                timeout=cfg.timeout,
                follow_redirects=False,
            )

            if response.status_code == 401:
                return Res(
                    False,
                    err="auth_required: Wayback requires IA_KEY/IA_SECRET",
                )

            location = (
                response.headers.get("location")
                or response.headers.get("content-location")
            )

            if location:
                return Res(True, location)

            if response.status_code >= 400:
                return Res(
                    False,
                    err=f"HTTP {response.status_code}: "
                        f"{response.text[:500]}",
                )

            return Res(
                False,
                err="No archive location returned",
            )

        except httpx.TimeoutException:
            return Res(False, err="timeout: Wayback request timed out")

        except httpx.RequestError as exc:
            return Res(
                False,
                err=f"connection_error: {str(exc)[:900]}",
            )

        except Exception as exc:
            return Res(False, err=str(exc)[:1000])

    def _submit_authenticated(self, url, headers):
        headers = dict(headers)
        headers["Authorization"] = (
            f"LOW {cfg.ia_key}:{cfg.ia_secret}"
        )

        try:
            response = httpx.post(
                self.save_url,
                headers=headers,
                data={
                    "url": url,
                    "skip_first_archive": "1",
                },
                timeout=cfg.timeout,
            )

            if response.status_code == 401:
                return Res(
                    False,
                    err="auth_required: Wayback credentials rejected",
                )

            if response.status_code >= 400:
                return Res(
                    False,
                    err=f"HTTP {response.status_code}: "
                        f"{response.text[:500]}",
                )

            try:
                data = response.json()
            except ValueError:
              
                return Res(
                    False,
                    err="Invalid JSON returned by Wayback",
                )

            if data.get("status") == "error":
              return Res(
                    False,
                    err=(
                        data.get("message")
                        or data.get("status_ext")
                        or "capture failed"
                    ),
                )

            aid = data.get("job_id")

            if not aid:
                return Res(
                    False,
                    err="No job_id returned",
                )

            for _ in range(24):
                status = httpx.get(
                    f"https://web.archive.org/save/status/{aid}",
                    headers=headers,
                    timeout=cfg.timeout,
                )

                if status.status_code == 401:
                    return Res(
                        False,
                        aid=aid,
                        err="auth_required: "
                            "Wayback credentials rejected",
                    )

                if status.status_code >= 400:
                    return Res(
                        False,
                        aid=aid,
                        err=f"HTTP {status.status_code}: "
                            f"{status.text[:500]}",
                    )

                try:
                    result = status.json()
                except ValueError:
                    return Res(
                        False,
                        aid=aid,
                        err="Invalid JSON returned by Wayback status",
                    )

                state = result.get("status")

                if state == "success":
                    timestamp = result.get("timestamp")
                    original = (
                        result.get("original_url")
                        or url
                    )

                    if not timestamp:
                        return Res(
                            False,
                            aid=aid,
                            err="Wayback succeeded without timestamp",
                        )

                    archive_url = (
                        "https://web.archive.org/web/"
                        f"{timestamp}/{original}"
                    )

                    return Res(
                        True,
                        archive_url,
                        aid,
                    )

                if state == "error":
                    return Res(
                        False,
                        aid=aid,
                        err=(
                            result.get("message")
                            or result.get("status_ext")
                            or "capture failed"
                        ),
                    )

                time.sleep(5)

            return Res(
                False,
                aid=aid,
                err="capture pending after timeout",
            )

        except httpx.TimeoutException:
            return Res(
                False,
                err="timeout: Wayback request timed out",
            )

        except httpx.RequestError as exc:
            return Res(
                False,
                err=f"connection_error: {str(exc)[:900]}",
            )

        except Exception as exc:
            return Res(False, err=str(exc)[:1000])

    def status(self, aid):
        try:
            response = httpx.get(
                f"https://web.archive.org/save/status/{aid}",
                timeout=cfg.timeout,
            )
            return response.json()
        except Exception:
            return {}
