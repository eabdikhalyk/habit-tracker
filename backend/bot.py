"""
Telegram-бot для борьбы с зависимостями (алкоголь, курение и т.д.).

Полностью самостоятельный: регистрация происходит прямо в Telegram,
без email/пароля от веб-аккаунта. Каждое утро бот спрашивает,
продержался ли пользователь, ведёт счётчик дней (streak) и фиксирует срывы.
"""
import os
import random
from datetime import date

from dotenv import load_dotenv
from pytz import timezone
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database import SessionLocal
from models import SobrietyCheckin, SobrietyRelapse, SobrietyUser

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TZ = timezone("Asia/Aqtobe")

ADDICTIONS = ["Алкоголь", "Курение", "Игры", "Сладкое", "Другое"]

MOTIVATIONAL_QUOTES = [
    "Каждый день без срыва — это победа, которую у тебя никто не отнимет. 💪",
    "Ты не должен быть идеальным, просто не сдавайся сегодня. 🔥",
    "Сила привычки слабее силы решения, принятого заново каждое утро. ☀️",
    "Тяга — это волна. Она поднимается и опускается. Ты её пережил уже не раз. 🌊",
    "Через год ты будешь рад, что не сдался сегодня. 🌱",
]

SOS_TIPS = [
    "Тяга длится в среднем 10-20 минут. Она пройдёт, даже если ничего не делать. Просто продержись эти минуты. ⏳",
    "Подышим: вдох на 4 счёта, задержка на 7, выдох на 8. Повтори 4 раза. 🫁",
    "Выпей стакан воды и пройдись по комнате/улице 5 минут. Смена позы сбивает тягу. 🚶",
    "Напиши сейчас одному человеку, который тебя поддерживает. Не обязательно про тягу — просто напиши. 📱",
    "Вспомни: зачем ты начал? Прочитай эту причину вслух. 🎯",
]


# ── Регистрация ───────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    db = SessionLocal()
    user = db.query(SobrietyUser).filter(SobrietyUser.telegram_id == chat_id).first()

    if user:
        await update.message.reply_text(
            f"Привет! Ты уже в системе.\n\n"
            f"Без «{user.addiction}» — {user.streak} дней 🔥\n"
            f"Рекорд: {user.max_streak} дней\n\n"
            f"/status — посмотреть прогресс\n"
            f"/relapse — отметить срыв\n"
            f"/sos — если сейчас тянет сорваться"
        )
        db.close()
        return

    db.close()
    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"register_{name}")]
        for name in ADDICTIONS
    ]
    await update.message.reply_text(
        "Привет! Я помогу тебе отказаться от зависимости.\n\n"
        "От чего хочешь избавиться?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    addiction = query.data.split("_", 1)[1]
    chat_id = str(update.effective_chat.id)

    db = SessionLocal()
    existing = db.query(SobrietyUser).filter(SobrietyUser.telegram_id == chat_id).first()
    if existing:
        await query.edit_message_text("Ты уже зарегистрирован ✅")
        db.close()
        return

    user = SobrietyUser(
        telegram_id=chat_id,
        addiction=addiction,
        start_date=date.today(),
        streak=0,
        max_streak=0,
        daily_cost=0,
    )
    db.add(user)
    db.commit()
    db.close()

    context.user_data["awaiting_cost"] = True
    await query.edit_message_text(
        f"Готово! Отслеживаю отказ от «{addiction}» с сегодняшнего дня. 🚀\n\n"
        f"Сколько в среднем тратил(а) на это в день (в тенге)?\n"
        f"Напиши число — буду показывать, сколько ты сэкономил. Если не хочешь считать — напиши 0."
    )


async def handle_cost_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_cost"):
        return

    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("Напиши просто число, например 1500 (или 0).")
        return

    chat_id = str(update.effective_chat.id)
    db = SessionLocal()
    user = db.query(SobrietyUser).filter(SobrietyUser.telegram_id == chat_id).first()
    if user:
        user.daily_cost = int(text)
        db.commit()
    db.close()

    context.user_data["awaiting_cost"] = False
    await update.message.reply_text(
        "Записал! 📊\n\n"
        "Каждое утро в 9:00 буду спрашивать, как дела.\n"
        "Команды:\n"
        "/status — прогресс и сэкономленные деньги\n"
        "/relapse — отметить срыв\n"
        "/sos — если сейчас тянет сорваться"
    )


# ── Статус ────────────────────────────────────────────────────────────────

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    db = SessionLocal()
    user = db.query(SobrietyUser).filter(SobrietyUser.telegram_id == chat_id).first()
    if not user:
        await update.message.reply_text("Сначала зарегистрируйся: /start")
        db.close()
        return

    days_total = (date.today() - user.start_date).days
    text = (
        f"📊 Без «{user.addiction}»\n\n"
        f"🔥 Текущий стрик: {user.streak} дней\n"
        f"🏆 Рекорд: {user.max_streak} дней\n"
        f"📅 Всего с начала пути: {days_total} дней"
    )
    if user.daily_cost:
        saved = user.streak * user.daily_cost
        text += f"\n💰 Сэкономлено: {saved} тенге"
    await update.message.reply_text(text)
    db.close()


async def sos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(random.choice(SOS_TIPS))


# ── Ежедневный чек-ин ─────────────────────────────────────────────────────

scheduler = AsyncIOScheduler()


@scheduler.scheduled_job("cron", hour=9, minute=0, timezone=TZ)
async def send_daily_checkin():
    db = SessionLocal()
    users = db.query(SobrietyUser).all()
    for user in users:
        keyboard = [[
            InlineKeyboardButton("✅ Держусь!", callback_data=f"holding_{user.id}"),
            InlineKeyboardButton("😔 Сорвался", callback_data=f"relapsed_{user.id}"),
        ]]
        await app.bot.send_message(
            chat_id=user.telegram_id,
            text=(
                f"Доброе утро! ☀️\n\n"
                f"🔥 Без «{user.addiction}» — {user.streak} дней\n"
                f"Как прошёл вчерашний день?"
            ),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    db.close()


async def handle_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    status_value, user_id_str = query.data.split("_")
    user_id = int(user_id_str)

    db = SessionLocal()
    user = db.query(SobrietyUser).filter(SobrietyUser.id == user_id).first()
    if not user:
        await query.edit_message_text("Пользователь не найден. Напиши /start")
        db.close()
        return

    today = date.today()

    if status_value == "holding":
        already = db.query(SobrietyCheckin).filter(
            SobrietyCheckin.user_id == user.id,
            SobrietyCheckin.date == today,
        ).first()
        if already:
            await query.edit_message_text("Ты уже отметился сегодня ✅")
            db.close()
            return

        db.add(SobrietyCheckin(user_id=user.id, date=today, status="holding"))
        user.streak += 1
        if user.streak > user.max_streak:
            user.max_streak = user.streak
        db.commit()

        quote = random.choice(MOTIVATIONAL_QUOTES)
        text = (
            f"Молодец! 🔥 Уже {user.streak} дней без «{user.addiction}»!\n"
            f"Рекорд: {user.max_streak} дней"
        )
        if user.daily_cost:
            text += f"\n💰 Сэкономлено: {user.streak * user.daily_cost} тенге"
        text += f"\n\n{quote}"
        await query.edit_message_text(text)
    else:
        await log_relapse(query, db, user, today)

    db.close()


async def log_relapse(query, db, user, today):
    already = db.query(SobrietyRelapse).filter(
        SobrietyRelapse.user_id == user.id,
        SobrietyRelapse.date == today,
    ).first()
    if already:
        await query.edit_message_text("Срыв сегодня уже отмечен.")
        return

    db.add(SobrietyRelapse(user_id=user.id, date=today, note=None))
    user.streak = 0
    db.commit()
    await query.edit_message_text(
        "Срыв записан. Не сдавайся, завтра новый день 💪\n"
        "Срывы — часть пути, а не его конец."
    )


# ── Ручная отметка срыва командой ────────────────────────────────────────

async def relapse_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    db = SessionLocal()
    user = db.query(SobrietyUser).filter(SobrietyUser.telegram_id == chat_id).first()
    if not user:
        await update.message.reply_text("Сначала зарегистрируйся: /start")
        db.close()
        return

    keyboard = [[InlineKeyboardButton("😔 Да, подтвердить срыв", callback_data=f"relapsed_{user.id}")]]
    await update.message.reply_text(
        "Точно хочешь отметить срыв? Стрик обнулится.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    db.close()


# ── Запуск ────────────────────────────────────────────────────────────────

async def on_startup(application):
    scheduler.start()


app = (
    Application.builder()
    .token(TOKEN)
    .post_init(on_startup)
    .build()
)
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("relapse", relapse_command))
app.add_handler(CommandHandler("sos", sos))
app.add_handler(CallbackQueryHandler(handle_register, pattern=r"^register_"))
app.add_handler(CallbackQueryHandler(handle_checkin, pattern=r"^(holding|relapsed)_"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_cost_input))

if __name__ == "__main__":
    app.run_polling()
