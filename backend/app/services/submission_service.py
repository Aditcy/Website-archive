from sqlalchemy import select, exists

from ..models import URL, Submission
from ..workers.tasks import sub


def make(db, did, service):
    rows = (
        db.execute(
            select(URL).where(
                URL.domain_id == did,
                URL.status == "ok",
                URL.http_status.is_not(None),
            )
        )
        .scalars()
        .all()
    )

    n = 0

    for u in rows:
        ok = db.execute(
            select(
                exists().where(
                    Submission.url_id == u.id,
                    Submission.service == service,
                    Submission.status == "success",
                )
            )
        ).scalar()

        if not ok:
            existing = db.execute(
                select(Submission).where(
                    Submission.url_id == u.id,
                    Submission.service == service,
                    Submission.status.in_(
                        ["queued", "processing", "retry", "manual"]
                    ),
                )
            ).scalar_one_or_none()

            if not existing:
                db.add(
                    Submission(
                        url_id=u.id,
                        service=service,
                        status="queued",
                    )
                )
                n += 1

    db.commit()

    queued = (
        db.execute(
            select(Submission)
            .join(Submission.url)
            .where(
                URL.domain_id == did,
                Submission.status == "queued",
                Submission.service == service,
            )
        )
        .scalars()
        .all()
    )

    for x in queued:
        sub.delay(x.id)

    return n
