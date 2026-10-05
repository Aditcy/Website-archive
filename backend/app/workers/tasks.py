from ..time import utcnow
from celery.exceptions import Retry

from .celery import cel
from ..archives import get
from ..config import cfg
from ..db import Ses, Session
from ..models import Submission
from ..crawler.engine import run


@cel.task(bind=True, max_retries=0)
def crawl(self, did, rid):
    run(did, rid)


@cel.task(bind=True, max_retries=cfg.retries)
def sub(self, sid):
    db_factory = Ses
    db = db_factory()
    owns_session = db_factory is Session

    try:
        x = db.get(Submission, sid)

        if not x or x.status == "success":
            return

        x.status = "processing"
        x.attempts += 1
        db.commit()

        provider = get(x.service)

        if not provider:
            x.status = "failed"
            x.error = f"Unknown archive service: {x.service}"
            db.commit()
            return

        result = provider.submit(x.url.norm)

        if result.ok:
            x.status = "success"
            x.archive_url = result.url
            x.submitted_at = utcnow()
            x.error = None
            db.commit()
            return

        if result.err == "manual_required":
            x.status = "manual"
            x.archive_url = result.url
            x.error = result.err
            x.submitted_at = utcnow()
            db.commit()
            return

        if result.err and result.err.startswith("auth_required:"):
            x.status = "failed"
            x.error = result.err
            db.commit()
            return

        error_text = str(result.err or "").casefold()

        permanent_errors = (
            "already been captured",
            "too-many-daily-captures",
            "too many daily captures",
            "daily limit",
            "captured 5 times today",
        )

        if any(marker in error_text for marker in permanent_errors):
            x.status = "failed"
            x.error = result.err
            db.commit()
            return

        if x.attempts < cfg.retries:
            x.status = "retry"
            x.error = result.err
            db.commit()

            raise self.retry(
                countdown=30 * x.attempts,
                exc=RuntimeError(
                    result.err or "archive submission failed"
                ),
            )

        x.status = "failed"
        x.error = result.err
        db.commit()

    except Retry:
        raise

    except Exception as e:
        db.rollback()

        x = db.get(Submission, sid)

        if x:
            x.status = "failed"
            x.error = str(e)[:1000]
            db.commit()

        raise

    finally:
        if owns_session:
            db.close()
