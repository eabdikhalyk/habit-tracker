from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    login = Column(String, unique=True, nullable=True)
    # ↑ ник для входа; nullable=True, чтобы существующие записи без login не ломали БД
    password = Column(String, nullable=False)
    telegram_id = Column(String, unique=True, nullable=True)
    # ↑ для Telegram бота — добавим позже
    created_at = Column(DateTime, server_default=func.now())

class BadHabit(Base):
    __tablename__ = "bad_habits"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    # ↑ например "Алкоголь", "Курение"
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    start_date = Column(Date, nullable=False)
    # ↑ когда начал бороться
    streak = Column(Integer, default=0)
    max_streak = Column(Integer, default=0)
    # ↑ дней без срыва
    frozen = Column(Integer, default=0)
    # ↑ 0 = активен, 1 = заморожен (не отвечал 2+ дня)
    created_at = Column(DateTime, server_default=func.now())

class Relapse(Base):
    __tablename__ = "relapses"

    id = Column(Integer, primary_key=True)
    habit_id = Column(Integer, ForeignKey("bad_habits.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    note = Column(Text, nullable=True)
    # ↑ пользователь может написать что случилось
    created_at = Column(DateTime, server_default=func.now())

class Checkin(Base):
    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True)
    habit_id = Column(Integer, ForeignKey("bad_habits.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    status = Column(String, nullable=False)
    # ↑ "holding" = держится, "relapsed" = сорвался, "no_response" = не ответил
    created_at = Column(DateTime, server_default=func.now())


# ── Telegram-бот для борьбы с зависимостями ──────────────────────────────
# Отдельные таблицы, без привязки к веб-аккаунту (User): регистрация
# происходит полностью внутри Telegram, email/пароль не нужны.

class SobrietyUser(Base):
    __tablename__ = "sobriety_users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, unique=True, nullable=False)
    addiction = Column(String, nullable=False)
    # ↑ например "Алкоголь", "Курение", "Другое"
    start_date = Column(Date, nullable=False)
    streak = Column(Integer, default=0)
    max_streak = Column(Integer, default=0)
    daily_cost = Column(Integer, default=0)
    # ↑ сколько в среднем тратил в день на зависимость (для счётчика сэкономленных денег)
    created_at = Column(DateTime, server_default=func.now())


class SobrietyCheckin(Base):
    __tablename__ = "sobriety_checkins"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("sobriety_users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    status = Column(String, nullable=False)
    # ↑ "holding" = держится, "relapsed" = сорвался
    created_at = Column(DateTime, server_default=func.now())


class SobrietyRelapse(Base):
    __tablename__ = "sobriety_relapses"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("sobriety_users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())