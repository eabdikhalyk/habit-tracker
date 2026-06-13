from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session 
from database import get_db
from models import User
from passlib.context import CryptContext
from jose import jwt    
from datetime import datetime, timedelta
from pydantic import BaseModel
import os
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"])
SECRET_KEY = os.getenv("SECRET_KEY")

class RegisterSchema(BaseModel):
    email: str
    password: str
    
class LoginSchema(BaseModel):
    email: str
    password: str
    
@router.post("/register")
def register(user: RegisterSchema, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email уже занят") 
    
    hashed_password = pwd_context.hash(user.password)
    user = User(email=user.email, password=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {"message": "Регистрация успешна", "user_id": user.id}

@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    # ↑ OAuth2 принимает form-data с полями username и password
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form_data.username).first()
    # ↑ username здесь это наш email
    if not user:
        raise HTTPException(status_code=401, detail="Неверный email или пароль")

    if not pwd_context.verify(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")

    payload = {
        "user_id": user.id,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    return {"access_token": token, "token_type": "bearer"}
    # ↑ OAuth2 требует именно такой формат ответа