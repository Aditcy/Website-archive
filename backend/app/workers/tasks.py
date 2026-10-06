from celery.exceptions import Retry

from .celery import cel
from ..archives import get
from ..config import cfg
from ..db import Ses
from ..models import Submission, Crawl
from ..crawler.engine import run
from ..time import utcnow


@cel.task(bind=True, max_retries=cfg.retries)
def crawl(self, did, rid):
    db = Ses()

    try:
        crawl_row = db.get(Crawl, rid)

        # The Celery message may have been sitting in Redis from an
        # earlier run. Never restart a crawl that is no longer queued.
        if not crawl_row:
            return

        if crawl_row.domain_id != did:
            return

        if crawl_row.status != "queued":
            return

        # Claim this crawl before doing any actual work.
        crawl_row.status = "running"
        crawl_row.started_at = crawl_row.started_at or utcnow()
        crawl_row.finished_at = None
        crawl_row.heartbeat = utcnow()
        crawl_row.error = None

        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()

    # The crawl engine now owns the actual crawling.
    run(did, rid)


@cel.task(bind=True, max_retries=cfg.retries)
def sub(self, sid):
    db = Ses()

    try:
        submission = db.get(
            Submission,
            sid,
        )

        if not submission:
            return

        if submission.status == "success":
            return

        submission.status = "processing"
        submission.attempts += 1
        db.commit()

        provider = get(submission.service)

        if not provider:
            submission.status = "failed"
            submission.error = (
                f"Unknown archive service: "
                f"{submission.service}"
            )
            db.commit()
            return

        result = provider.submit(
            submission.url.norm
        )

        if result.ok:
            submission.status = "success"
            submission.archive_url = result.url
            submission.error = None
            submission.submitted_at = utcnow()
            db.commit()
            return

        error_text = str(
            result.err or "archive submission failed"
        )

        lowered = error_text.casefold()

        permanent_errors = (
            "auth_required:",
            "already been captured",
            "too-many-daily-captures",
            "too many daily captures",
            "daily limit",
            "captured 5 times today",
            "invalid url",
        )

        if (
            result.err == "manual_required"
            or any(
                marker in lowered
                for marker in permanent_errors
            )
        ):
            submission.status = (
                "manual"
                if result.err == "manual_required"
                else "failed"
            )

            submission.archive_url = result.url
            submission.error = error_text

            if result.err == "manual_required":
                submission.submitted_at = utcnow()

            db.commit()
            return

        if submission.attempts <= cfg.retries:
            submission.status = "retry"
            submission.error = error_text
            db.commit()

            raise self.retry(
                countdown=30 * submission.attempts,
                exc=RuntimeError(error_text),
            )

        submission.status = "failed"
        submission.error = error_text
        db.commit()

    except Retry:
        raise

    except Exception as exc:
        db.rollback()

        submission = db.get(
            Submission,
            sid,
        )

        if not submission:
            return

        error_text = str(exc)[:1000]

        if submission.attempts <= cfg.retries:
            submission.status = "retry"
            submission.error = error_text
            db.commit()

            raise self.retry(
                countdown=30 * submission.attempts,
                exc=exc,
            )

        submission.status = "failed"
        submission.error = error_text
        db.commit()

    finally:
        db.close()
