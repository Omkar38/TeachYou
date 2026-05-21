from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def make_session_factory(dsn: str):
    engine = create_engine(dsn, pool_pre_ping=True)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False), engine
