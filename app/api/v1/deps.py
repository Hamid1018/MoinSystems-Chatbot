from app.db.session import SessionLocal # Assuming this is your SQLAlchemy session maker

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()