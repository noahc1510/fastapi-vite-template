from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import config

engine = create_engine(
    config.sqlalchemy_database_uri,
    pool_size=config.POSTGRES_POOL_SIZE,
    max_overflow=config.POSTGRES_MAX_OVERFLOW,
    connect_args={"options": f"-c timezone={config.POSTGRES_TIMEZONE}"},
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()