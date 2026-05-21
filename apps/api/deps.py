# from collections.abc import Generator

# from sqlalchemy.orm import Session

# from apps.api.settings import settings
# from db.session import make_session_factory

# SessionLocal, engine = make_session_factory(settings.postgres_dsn)


# def get_db() -> Generator[Session, None, None]:
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()
from __future__ import annotations

from typing import Generator

from sqlalchemy.orm import Session

from apps.api.settings import settings
from db.session import make_session_factory

SessionLocal, engine = make_session_factory(settings.database_dsn)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
