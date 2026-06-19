from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import BadHabit, Relapse, Checkin
from dependencies import get_current_user
from models import User
from pydantic import BaseModel
from datetime import date
router = APIRouter()

class HabitSchema(BaseModel):
    title: str
    # ↑ например "Алкоголь", "Курение"

class RelapseSchema(BaseModel):
    note: str | None = None
    # ↑ опциональная заметка; str | None разрешает И отсутствие поля, И явный null

# Создать вредную привычку
@router.post("/")
def create_habit(
    data: HabitSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    habit = BadHabit(
        title=data.title,
        user_id=current_user.id,
        start_date=date.today()
        # ↑ начинаем отсчёт с сегодня
    )
    db.add(habit)
    db.commit()
    db.refresh(habit)
    return habit

# Получить все привычки пользователя
@router.get("/")
def get_habits(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    habits = db.query(BadHabit).filter(BadHabit.user_id == current_user.id).all()
    return habits

@router.get("/{habit_id}/relapses")
def get_relapse(habit_id:int,
                db: Session = Depends(get_db), 
                current_user: User = Depends(get_current_user)):
    habit = db.query(BadHabit).filter(BadHabit.id == habit_id, BadHabit.user_id == current_user.id).first()
    
    if not habit:
        raise HTTPException(status_code=404, detail="Привычка не найдена")
    
    relapses = db.query(Relapse).filter(Relapse.habit_id == habit.id).all()
    return relapses    

# Зафиксировать срыв
@router.post("/{habit_id}/relapse")
def record_relapse(
    habit_id: int,
    data: RelapseSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    habit = db.query(BadHabit).filter(
        BadHabit.id == habit_id,
        BadHabit.user_id == current_user.id
    ).first()

    if not habit:
        raise HTTPException(status_code=404, detail="Привычка не найдена")

    # Записываем срыв
    relapse = Relapse(
        habit_id=habit_id,
        date=date.today(),
        note=data.note
    )
    db.add(relapse)

    # Обнуляем streak
    habit.streak = 0
    db.commit()

    return {"message": "Срыв записан. Не сдавайся, завтра новый день 💪"}

# Ежедневный чекин — держусь
@router.post("/{habit_id}/checkin")
def daily_checkin(
    habit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    habit = db.query(BadHabit).filter(
        BadHabit.id == habit_id,
        BadHabit.user_id == current_user.id
    ).first()

    if not habit:
        raise HTTPException(status_code=404, detail="Привычка не найдена")

    # Проверяем — не чекинился ли уже сегодня
    existing = db.query(Checkin).filter(
        Checkin.habit_id == habit_id,
        Checkin.date == date.today()
    ).first()

    if existing:
        return {"message": "Ты уже отметился сегодня ✅"}

    # Записываем чекин
    checkin = Checkin(
        habit_id=habit_id,
        date=date.today(),
        status="holding"
    )
    db.add(checkin)

    # Увеличиваем streak
    habit.streak += 1
    db.commit()

    return {
        "message": f"Молодец! Держишься уже {habit.streak} дней 🔥",
        "streak": habit.streak
    }


@router.delete("/{habit_id}")
def delete_habit(habit_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
        habit = db.query(BadHabit).filter(
            BadHabit.id == habit_id,
            BadHabit.user_id == current_user.id
        ).first()

        if not habit:
            raise HTTPException(status_code=404, detail="Привычка не найдена")

        db.delete(habit)
        db.commit()
        return {"message": "Привычка удалена"}
    
@router.get("/{habit_id}/streak")
def get_streak(habit_id: int, db: Session = Depends(get_db),current_user: User = Depends(get_current_user)):
    
    habit = db.query(BadHabit).filter(BadHabit.id == habit_id, BadHabit.user_id == current_user.id).first()
    if not habit:
            raise HTTPException(status_code=404, detail="Привычка не найдена")
    else:
        days_total = (date.today() - habit.start_date).days
        return {"streak":habit.streak, "start_date":habit.start_date, "days_total":days_total}
    
