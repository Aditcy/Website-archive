from sqlalchemy import select

from ..models import URL, Submission


def new(db, did):
    return (
        db.execute(
            select(URL).where(
                URL.domain_id == did,
                ~URL.submissions.any(Submission.status == "success"),
            )
        )
        .scalars()
        .all()
    )
