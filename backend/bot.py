from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from database import SessionLocal
from models import User
import os
from pytz import timezone
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from models import BadHabit, Relapse, Checkin
from datetime import date
from telegram.ext import CallbackQueryHandler

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def on_startup(app):
    print("=== on_startup вызван ===")
    scheduler.start()
    print("=== scheduler запущен ===")

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

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job("cron", hour=6, minute=42, timezone=timezone("Asia/Aqtobe"))
async def send_daily_checkin():
    print("=== scheduler запустился ===")
    
    bot =app.bot
    db = SessionLocal()
    users = db.query(User).filter(User.telegram_id != None).all()
    print(f"Пользователей с telegram_id: {len(users)}")
    for user in users:
        habit = db.query(BadHabit).filter(BadHabit.user_id == user.id).first()
        print(f"Привычка пользователя {user.id}: {habit}")
        if not habit:
            continue
        print(f"Отправляю сообщение на {user.telegram_id}")
        keyboard = [[
        InlineKeyboardButton("✅ Держусь!", callback_data=f"holding_{habit.id}"),
        InlineKeyboardButton("😔 Сорвался", callback_data=f"relapsed_{habit.id}"),
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await bot.send_message(chat_id=user.telegram_id, text=f"Как прошёл день?\n\n🔥 Без {habit.title} — {habit.streak} дней\nДержишься?", reply_markup=reply_markup)
    
    db.close()


async def handle_checkin(update, context):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    status = parts[0]
    habit_id = int(parts[1])
    
    db = SessionLocal()
    habit = db.query(BadHabit).filter(BadHabit.id == habit_id).first()
    if status == "holding":
        existing = db.query(Checkin).filter(
        Checkin.habit_id == habit.id,
        Checkin.date == date.today()
        ).first()
        
        if existing:
            await query.message.reply_text("Ты уже отметился сегодня ✅")
            db.close()
            return

        checkin = Checkin(
        habit_id=habit_id,
        date=date.today(),
        status="holding"
        )
        db.add(checkin)

        # Увеличиваем streak
        habit.streak += 1
        
        if habit.streak > habit.max_streak:
            habit.max_streak = habit.streak
            
        db.commit()
        await query.message.reply_text(f"Молодец! 🔥 Уже {habit.streak} дней!\n"
                                        f"Твой рекорд: {habit.max_streak} дней")
    else:
        existing = db.query(Relapse).filter(
        Relapse.habit_id == habit_id,
        Relapse.date == date.today()
        ).first()
        
        if existing:
            await query.message.reply_text("Ты уже отметился сегодня ✅")
            db.close()
            return
        # Записываем срыв
        relapse = Relapse(
        habit_id=habit_id,
        date=date.today(),
        note = None
        )
        db.add(relapse)

        # Обнуляем streak
        habit.streak = 0
        db.commit()

        await query.message.reply_text("Срыв записан. Не сдавайся, завтра новый день 💪")  

    db.close()

# ↓ сначала регистрируем handlers
app = (
    Application.builder()
    .token(TOKEN)
    .post_init(on_startup)
    .build()
)
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, link_account))
app.add_handler(CallbackQueryHandler(handle_checkin))

# ↓ потом запускаем
app.run_polling()