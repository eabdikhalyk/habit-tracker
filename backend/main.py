import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, habits

# Схемой БД теперь управляет Alembic (alembic upgrade head), а не create_all.
# Это единый источник правды о структуре таблиц на всех окружениях.

app = FastAPI(title="Habit Tracker API")

# CORS — список разрешённых origin берём из env (через запятую).
# Локально это http://localhost:3000, на проде — домен задеплоенного фронта.
# Без этого браузер блокирует запросы с другого origin (Same-Origin Policy).
origins = os.getenv("FRONTEND_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(habits.router, prefix="/habits", tags=["habits"])

@app.get("/")
def root():
    return {"message": "Habit Tracker работает! 🔥"}

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}

