from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Create a standard synchronous engine
engine = create_engine(
    settings.database_url,
    echo=(settings.app_env == "development")
)

# Use standard sessionmaker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Standard generator
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()