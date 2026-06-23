"""
Telegram-бot для борьбы с зависимостями (алкоголь, курение и т.д.).

Полностью самостоятельный: регистрация происходит прямо в Telegram,
без email/пароля от веб-аккаунта. Каждое утро бот спрашивает,
продержался ли пользователь, ведёт счётчик дней (streak) и фиксирует срывы.
"""
import os
import random
from datetime import date

import httpx
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
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.1-8b-instant"
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


# ── AI-коуч (Groq, бесплатный tier, Llama 3.1) ───────────────────────────
# Без ключа бот не падает — просто молча переходит на статичные подсказки
# (SOS_TIPS) везде, где обычно отвечал бы ИИ.

def coach_system_prompt(addiction: str) -> str:
    return (
        f"Сначала определи, к какой именно категории относится зависимость «{addiction}», и стань "
        f"профессиональным психологом-коучем, который специализируется ИМЕННО на этом виде зависимости — "
        f"используй термины, триггеры и техники, специфичные для неё, а не общие фразы. Примеры подхода: "
        f"если это алкоголь — говори как специалист по алкогольной зависимости (триггеры срыва, детокс, "
        f"социальное давление выпить); если курение — как специалист по никотиновой зависимости (физическая "
        f"тяга, привычные ритуалы); если порнография — как специалист по преодолению порнозависимости "
        f"(влияние на мозг и дофамин, восприятие отношений); если игры/гемблинг — как специалист по игровой "
        f"зависимости (азарт, погоня за отыгрышем); если сладкое/еда — как специалист по пищевым привычкам. "
        f"Если зависимость другая — определи её природу сам и подстройся аналогично. "
        f"Ты современный, образованный, говоришь тёплым, дружеским и уверенным тоном, без занудства и "
        f"канцелярщины. Учитывай реальную жизнь человека: стресс на работе, соцсети, давление окружения. "
        f"Используй доказательные психологические техники (КПТ, работа с триггерами, привычками, "
        f"мотивационное интервью) и объясняй их простыми словами. "
        f"Не ставь точных медицинских диагнозов, не осуждай и не запугивай. Отвечай на русском языке, коротко "
        f"(3-5 предложений), и заверши конкретным практическим шагом, который поможет не сорваться прямо сейчас."
    )


async def ask_ai_coach(system_prompt: str, user_message: str, max_tokens: int = 800) -> str | None:
    if not GROQ_API_KEY:
        return None

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.9,
    }
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def support_phrase_prompt(addiction: str) -> str:
    return (
        f"Ты — тёплый, современный психолог-коуч, который коротко поддерживает человека, "
        f"избавляющегося от зависимости «{addiction}». Напиши ОДНУ короткую фразу поддержки "
        f"(до 12 слов, можно с эмодзи), каждый раз разную и не банальную. Не повторяй заданные ранее фразы. "
        f"Отвечай только этой фразой, без вступлений и кавычек."
    )


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
            f"/sos — если сейчас тянет сорваться (ИИ-коуч даст совет)"
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
    db.close()

    if addiction == "Другое":
        context.user_data["awaiting_custom_addiction"] = True
        await query.edit_message_text("Напиши текстом, от чего хочешь избавиться:")
        return

    create_sobriety_user(chat_id, addiction)
    context.user_data["awaiting_cost"] = True
    await query.edit_message_text(
        f"Готово! Отслеживаю отказ от «{addiction}» с сегодняшнего дня. 🚀\n\n"
        f"Сколько в среднем тратил(а) на это в день (в тенге)?\n"
        f"Напиши число — буду показывать, сколько ты сэкономил. Если не хочешь считать — напиши 0."
    )


def create_sobriety_user(chat_id: str, addiction: str):
    db = SessionLocal()
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


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    text = update.message.text.strip()

    if context.user_data.get("awaiting_custom_addiction"):
        context.user_data["awaiting_custom_addiction"] = False
        create_sobriety_user(chat_id, text)
        context.user_data["awaiting_cost"] = True
        await update.message.reply_text(
            f"Готово! Отслеживаю отказ от «{text}» с сегодняшнего дня. 🚀\n\n"
            f"Сколько в среднем тратил(а) на это в день (в тенге)?\n"
            f"Напиши число — буду показывать, сколько ты сэкономил. Если не хочешь считать — напиши 0."
        )
        return

    if context.user_data.get("awaiting_cost"):
        if not text.isdigit():
            await update.message.reply_text("Напиши просто число, например 1500 (или 0).")
            return

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
            "/sos — если сейчас тянет сорваться (ИИ-коуч даст совет)"
        )
        return

    # Свободный текст вне сценариев регистрации — ИИ здесь не отвечает, только /sos.
    await update.message.reply_text(
        "Если тянет сорваться — напиши /sos, ИИ-коуч даст совет.\nДля прогресса — /status."
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
    chat_id = str(update.effective_chat.id)
    db = SessionLocal()
    user = db.query(SobrietyUser).filter(SobrietyUser.telegram_id == chat_id).first()
    db.close()

    addiction = user.addiction if user else "плохая привычка"
    ai_reply = await ask_ai_coach(
        coach_system_prompt(addiction),
        "Мне прямо сейчас очень хочется сорваться. Помоги продержаться.",
    )
    await update.message.reply_text(ai_reply or random.choice(SOS_TIPS))


# ── Ежедневный чек-ин ─────────────────────────────────────────────────────

scheduler = AsyncIOScheduler()


@scheduler.scheduled_job("cron", hour=9, minute=0, timezone=TZ)
async def send_daily_checkin():
    today = date.today()
    db = SessionLocal()
    users = db.query(SobrietyUser).all()
    for user in users:
        # Атомарно "забираем" право отправить напоминание этому пользователю сегодня.
        # Если параллельно запущен второй инстанс бота, он увидит rowcount == 0
        # (дата уже проставлена) и пропустит отправку — так дубли невозможны.
        claimed = db.query(SobrietyUser).filter(
            SobrietyUser.id == user.id,
            (SobrietyUser.last_reminder_date == None) | (SobrietyUser.last_reminder_date < today),  # noqa: E711
        ).update({"last_reminder_date": today}, synchronize_session=False)
        db.commit()
        if not claimed:
            continue

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

        ai_quote = await ask_ai_coach(
            support_phrase_prompt(user.addiction),
            f"Я продержался {user.streak} дней без {user.addiction}. Поддержи меня коротко.",
            max_tokens=60,
        )
        quote = ai_quote or random.choice(MOTIVATIONAL_QUOTES)
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
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

if __name__ == "__main__":
    app.run_polling()
