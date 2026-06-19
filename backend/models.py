from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from database import Base


# ── Telegram-бот для борьбы с зависимостями ──────────────────────────────
# Регистрация происходит полностью внутри Telegram, email/пароль не нужны.

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
