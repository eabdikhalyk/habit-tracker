from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import engine, get_db
import models

models.Base.metadata.create_all(bind=engine)
# ↑ создаёт таблицы в БД если их нет

app = FastAPI(title="Habit Tracker API")

@app.get("/")
def root():
    return {"message": "Habit Tracker работает! 🔥"}

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}

@app.get("/habits")
def get_habits(db:Session = Depends(get_db)):
    # ↑ db — сессия базы данных, Depends автоматически её передаёт
    habits = db.query(models.Habit).all()
    # ↑ SELECT * FROM habits
    return habits

@app.post("/habits")
def create_habit(title: str, db: Session = Depends(get_db)):
    habit = models.Habit(title=title)
    # ↑ создаём объект привычки
    db.add(habit)
    # ↑ добавляем в сессию
    db.commit()
    # ↑ сохраняем в БД
    db.refresh(habit)
    # ↑ обновляем объект — получаем id из БД
    return habit
@app.post("habits/{habit_id}")
def update_habit(habit_id:int, title: str, db: Session = Depends(get_db)):
    habit = db.query(models.Habit).filter(models.Habit.id == habit_id).first()
    # ↑ SELECT * FROM habits WHERE id = habit_id
    if not habit:
        return {"error": "Привычка не найдена"}
    
    habit.title = title
    db.commit()
    db.refresh(habit)
    return habit

@app.delete("/habits/{habit_id}")
def delete_habit(habit_id: int, db: Session = Depends(get_db)):
    habit = db.query(models.Habit).filter(models.Habit.id == habit_id).first()
    if not habit:
        return {"error": "Привычка не найдена"}
    
    db.delete(habit)
    db.commit()
    return {"message": "Привычка удалена"}
    