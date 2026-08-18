from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# SQLite: enable WAL mode and foreign keys
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=settings.DEBUG,
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a DB session and ensures it is closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Called on app startup."""
    # Import all models so SQLAlchemy knows about them before create_all
    from app.models import (  # noqa: F401
        Medicine, Batch, StockLog, Sale, ExpiryLog, Prediction, User,
        PackInstance, DispenseTransaction, DispenseLineItem, WriteOff,
        ReconciliationAdjustment, CDRegisterEntry, DutyRegisterEntry, CDDestructionRecord,
    )
    Base.metadata.create_all(bind=engine)
