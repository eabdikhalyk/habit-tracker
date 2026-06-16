from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from database import SessionLocal
from models import User
import os

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        f"Привет! Твой Telegram ID: {chat_id}\n\nНапиши свой email чтобы привязать аккаунт:"
    )

async def link_account(update, context):
    email = update.message.text
    chat_id = update.effective_chat.id

    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()

    if not user:
        await update.message.reply_text("Пользователь не найден")
        db.close()
        return

    user.telegram_id = str(chat_id)
    db.commit()
    await update.message.reply_text("Аккаунт привязан! ✅ Теперь буду напоминать тебе каждый день.")
    db.close()

# ↓ сначала регистрируем handlers
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, link_account))

# ↓ потом запускаем
app.run_polling()