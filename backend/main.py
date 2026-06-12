from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import engine, get_db
import models
from routes import auth, habits

models.Base.metadata.create_all(bind=engine)
# ↑ создаёт таблицы в БД если их нет

app = FastAPI(title="Habit Tracker API")

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(habits.router, prefix="/habits", tags=["habits"])

@app.get("/")
def root():
    return {"message": "Habit Tracker работает! 🔥"}

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}

