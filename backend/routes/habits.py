from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import BadHabit, User
from dependencies import get_current_user
from pydantic import BaseModel

router = APIRouter()

class HabitSchema(BaseModel):
    title: str

@router.get("/")
def get_habits(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
    # ↑ Depends(get_current_user) — проверяет токен и возвращает пользователя
):
    habits = db.query(BadHabit).filter(BadHabit.user_id == current_user.id).all()
    # ↑ только привычки текущего пользователя
    return habits

@router.post("/")
def create_habit(
    data: HabitSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    habit = BadHabit(title=data.title, user_id=current_user.id)
    # ↑ привязываем привычку к пользователю автоматически
    db.add(habit)
    db.commit()
    db.refresh(habit)
    return habit

@router.delete("/{habit_id}")
def delete_habit(
    habit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    habit = db.query(BadHabit).filter(
        BadHabit.id == habit_id,
        BadHabit.user_id == current_user.id
        # ↑ важно! проверяем что привычка принадлежит именно этому пользователю
    ).first()

    if not habit:
        raise HTTPException(status_code=404, detail="Привычка не найдена")

    db.delete(habit)
    db.commit()
    return {"message": "Привычка удалена"}