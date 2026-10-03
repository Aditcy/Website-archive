from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import cfg

engine = create_engine(cfg.db, pool_pre_ping=True)

Session = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()


# Compatibility aliases used by the existing API/worker code.
get = get_db
Ses = Session


def init():
    # Import models so SQLAlchemy registers their tables with Base.metadata.
    from .models import Domain, URL, Crawl, Submission  # noqa: F401

    Base.metadata.create_all(bind=engine)
