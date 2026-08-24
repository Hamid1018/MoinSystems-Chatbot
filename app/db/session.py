from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Force the URL to use the synchronous psycopg2 driver
db_url = settings.database_url

if db_url.startswith("postgresql+asyncpg://"):
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
elif db_url.startswith("postgres://"): 
    # Handles older Postgres URI formats automatically
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)

# Create a standard synchronous engine using the corrected URL
engine = create_engine(
    db_url,
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