from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import BACKEND_ROOT, get_settings


class Base(DeclarativeBase):
    pass


def _resolve_sqlite_url(database_url: str) -> str:
    prefix = "sqlite:///./"
    if database_url.startswith(prefix):
        relative_path = database_url.removeprefix(prefix)
        absolute_path = BACKEND_ROOT / relative_path
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{absolute_path.as_posix()}"
    return database_url


settings = get_settings()
SQLALCHEMY_DATABASE_URL = _resolve_sqlite_url(settings.database_url)

connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    # Import models before create_all so SQLAlchemy registers table metadata.
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_database_path() -> Path | None:
    if not SQLALCHEMY_DATABASE_URL.startswith("sqlite:///"):
        return None
    return Path(SQLALCHEMY_DATABASE_URL.removeprefix("sqlite:///"))
