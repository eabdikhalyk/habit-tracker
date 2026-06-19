from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL")


if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# SSL принудительно НЕ навязываем: внутренний адрес Railway
# (postgres.railway.internal) SSL не поддерживает, а sslmode=require там всё ломает.
# По умолчанию psycopg2 использует sslmode=prefer — сам решает по возможностям сервера.

# connect_timeout — чтобы коннект не висел вечно, а падал с понятной ошибкой.
engine = create_engine(DATABASE_URL, connect_args={"connect_timeout": 15})

SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()