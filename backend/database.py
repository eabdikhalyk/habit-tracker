from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()  # читаем .env файл

DATABASE_URL = os.getenv("DATABASE_URL")
# ↑ берём URL из .env, не пишем пароли в коде

engine = create_engine(DATABASE_URL)
# ↑ создаём подключение к PostgreSQL

SessionLocal = sessionmaker(bind=engine)
# ↑ фабрика сессий — каждый запрос получает свою сессию

Base = declarative_base()
# ↑ базовый класс для всех моделей

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
# ↑ даём сессию роуту и закрываем после запроса