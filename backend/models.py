from sqlalchemy import Column, Integer, String, ForeignKey
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    # ↑ unique=True — два пользователя с одним email невозможны
    password = Column(String)
    # ↑ здесь будет хэш, не сам пароль

class Habit(Base):
    __tablename__ = "habits"
    # ↑ название таблицы в PostgreSQL

    id = Column(Integer, primary_key=True)
    # ↑ уникальный ID каждой привычки

    title = Column(String)
    # ↑ название привычки

    streak = Column(Integer, default=0)
    # ↑ сколько дней подряд выполнена
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)