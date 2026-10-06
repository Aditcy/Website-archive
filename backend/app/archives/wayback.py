import time

import httpx

from ..config import cfg
from .base import Arch, Res


class Way(Arch):
    name = "wayback"

    save_url = "https://web.archive.org/save"
    status_url = "https://web.archive.org/save/status"

    def submit(self, url: str) -> Res:
        url = url.strip()

        if not url:
            return Res(
                ok=False,
                err="invalid URL: empty URL",
            )

        if not cfg.ia_key or not cfg.ia_secret:
            return Res(
                ok=False,
                err=(
                    "auth_required: IA_KEY and IA_SECRET "
                    "are required for Wayback submission"
                ),
            )

        headers = {
            "Accept": "application/json",
            "User-Agent": cfg.user_agent,
            "Authorization": (
                f"LOW {cfg.ia_key}:{cfg.ia_secret}"
            ),
        }

        data = {
            "url": url,
            "capture_all": "1",
            "delay_wb_availability": "1",
            "skip_first_archive": "1",
        }

        try:
            response = httpx.post(
                self.save_url,
                headers=headers,
                data=data,
                timeout=cfg.timeout,
                follow_redirects=False,
            )

            if response.status_code == 401:
                return Res(
                    ok=False,
                    err="auth_required: Wayback credentials rejected",
                )

            if response.status_code >= 400:
                return Res(
                    ok=False,
                    err=(
                        f"HTTP {response.status_code}: "
                        f"{response.text[:1000]}"
                    ),
                )

            try:
                result = response.json()
            except ValueError:
                return Res(
                    ok=False,
                    err=(
                        "Wayback returned non-JSON response: "
                        f"{response.text[:1000]}"
                    ),
                )

            if not isinstance(result, dict):
                return Res(
                    ok=False,
                    err="Wayback returned an invalid response",
                )

            if result.get("status") == "error":
                return Res(
                    ok=False,
                    err=(
                        result.get("message")
                        or result.get("status_ext")
                        or "Wayback capture failed"
                    ),
                )

            job_id = result.get("job_id")

            # Some successful responses may already contain
            # the final URL.
            immediate_url = (
                result.get("archive_url")
                or result.get("archiveUrl")
            )

            if immediate_url:
                return Res(
                    ok=True,
                    url=str(immediate_url),
                    aid=str(job_id) if job_id else None,
                )

            if not job_id:
                return Res(
                    ok=False,
                    err=(
                        "Wayback did not return a job_id: "
                        f"{result}"
                    ),
                )

            # Poll the Save Page Now job.
            for attempt in range(24):
                time.sleep(5)

                status = self._get_status(
                    str(job_id),
                )

                if not status:
                    continue

                state = status.get("status")

                if state == "success":
                    timestamp = status.get("timestamp")
                    original_url = (
                        status.get("original_url")
                        or url
                    )

                    if not timestamp:
                        return Res(
                            ok=False,
                            aid=str(job_id),
                            err=(
                                "Wayback capture succeeded "
                                "but no timestamp was returned"
                            ),
                        )

                    archive_url = (
                        "https://web.archive.org/web/"
                        f"{timestamp}/"
                        f"{original_url}"
                    )

                    return Res(
                        ok=True,
                        url=archive_url,
                        aid=str(job_id),
                    )

                if state == "error":
                    return Res(
                        ok=False,
                        aid=str(job_id),
                        err=(
                            status.get("message")
                            or status.get("status_ext")
                            or "Wayback capture failed"
                        ),
                    )

            return Res(
                ok=False,
                aid=str(job_id),
                err=(
                    "capture pending after 120 seconds; "
                    f"job_id={job_id}"
                ),
            )

        except httpx.TimeoutException:
            return Res(
                ok=False,
                err="timeout: Wayback request timed out",
            )

        except httpx.RequestError as exc:
            return Res(
                ok=False,
                err=(
                    "connection_error: "
                    f"{str(exc)[:900]}"
                ),
            )

        except Exception as exc:
            return Res(
                ok=False,
                err=str(exc)[:1000],
            )

    def _get_status(self, job_id: str) -> dict:
        headers = {
            "Accept": "application/json",
            "User-Agent": cfg.user_agent,
            "Authorization": (
                f"LOW {cfg.ia_key}:{cfg.ia_secret}"
            ),
        }

        try:
            response = httpx.get(
                f"{self.status_url}/{job_id}",
                headers=headers,
                timeout=cfg.timeout,
                follow_redirects=True,
            )

            if response.status_code == 401:
                return {
                    "status": "error",
                    "message": (
                        "auth_required: "
                        "Wayback credentials rejected"
                    ),
                }

            if response.status_code >= 400:
                return {
                    "status": "error",
                    "message": (
                        f"HTTP {response.status_code}: "
                        f"{response.text[:500]}"
                    ),
                }

            try:
                result = response.json()
            except ValueError:
                return {
                    "status": "error",
                    "message": (
                        "Wayback status returned "
                        "non-JSON response"
                    ),
                }

            if isinstance(result, dict):
                return result

            return {}

        except httpx.TimeoutException:
            return {}

        except httpx.RequestError:
            return {}

        except Exception:
            return {}

    def status(self, aid: str) -> dict:
        if not aid:
            return {}

        return self._get_status(aid)
