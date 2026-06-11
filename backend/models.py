from sqlalchemy import Column, Integer, String
from database import Base

class Habit(Base):
    __tablename__ = "habits"
    # ↑ название таблицы в PostgreSQL

    id = Column(Integer, primary_key=True)
    # ↑ уникальный ID каждой привычки

    title = Column(String)
    # ↑ название привычки

    streak = Column(Integer, default=0)
    # ↑ сколько дней подряд выполнена