from app.db.session import engine, SessionLocal
from app.db.model import Base

def init_db() -> None:
    """
    Initialize database tables and seed initial data.
    """

    # Import models to ensure they are registered with SQLAlchemy metadata.
    import app.db.model  # noqa: F401

    Base.metadata.create_all(bind=engine)