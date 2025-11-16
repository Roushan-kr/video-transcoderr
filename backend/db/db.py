from sqlalchemy import create_engine
from sec_keys import SecretKeys
from sqlalchemy.orm import sessionmaker

sks = SecretKeys()

engine = create_engine(sks.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db #not return because we want to use it as a generator
    finally:
        db.close()