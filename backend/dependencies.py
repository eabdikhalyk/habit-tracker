from fastapi import Depends, HTTPException, Header
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from database import get_db
from models import User
import os

SECRET_KEY = os.getenv("SECRET_KEY")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
# ↑ говорим Swagger где получать токен — появится кнопка Authorize

def get_current_user(
    authorization: str = Header(...),
    # ↑ читаем заголовок Authorization из запроса
    db: Session = Depends(get_db)
):
    try:
        # Убираем "Bearer " из начала токена
        token = authorization.replace("Bearer ", "")

        # Расшифровываем токен
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])

        # Достаём user_id из токена
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Неверный токен")

    except JWTError:
        raise HTTPException(status_code=401, detail="Неверный токен")

    # Ищем пользователя в БД
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    return user
    # ↑ возвращаем объект пользователя — роут получит его автоматически