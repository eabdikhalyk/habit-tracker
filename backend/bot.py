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

ADDICTIONS = ["Алкоголь", "Темекі шегу", "Ойын", "Тәтті", "Басқа"]

MOTIVATIONAL_QUOTES = [
    "Сырылмаған әр күн — ешкім тартып ала алмайтын жеңісің. 💪",
    "Мінсіз болуың міндетті емес, бүгін жай ғана берілме. 🔥",
    "Әдеттің күші әр таңда қайта қабылданған шешімнің күшінен әлдеқайда төмен. ☀️",
    "Құмарлық — толқын сияқты. Көтеріліп, содан кейін басылады. Сен оны бірнеше рет бастан өткіздің. 🌊",
    "Бір жылдан кейін бүгін бермегеніңе қуанасың. 🌱",
]

SOS_TIPS = [
    "Құмарлық орта есеппен 10-20 минут жалғасады. Ештеңе істемесең де, ол өтіп кетеді. Осы минутты шыда. ⏳",
    "Дем алайық: 4 санда дем ал, 7 санда ұста, 8 санда шығар. 4 рет қайтала. 🫁",
    "Бір стакан су іш және 5 минут бөлмеде/көшеде серуендеп жүр. Қалыпты өзгерту құмарлықты басады. 🚶",
    "Қазір сені қолдайтын біреуге жаз. Құмарлық туралы болуы міндетті емес — жай ғана жаз. 📱",
    "Есіңе ал: неге бастадың? Осы себепті дауыстап оқы. 🎯",
]


# ── AI-коуч (Groq, бесплатный tier, Llama 3.1) ───────────────────────────
# Без ключа бот не падает — просто молча переходит на статичные подсказки
# (SOS_TIPS) везде, где обычно отвечал бы ИИ.

def coach_system_prompt(addiction: str) -> str:
    return (
        f"Сен — қазіргі заманғы, білімді мұсылман ұстазсың (заман талабын түсінетін жас устаз сияқты), "
        f"«{addiction}» тәуелділігінен арылуға көмектесесің. Сөйлеу мәнерің — жылы, дос-бауырлас "
        f"сияқты («бауырым» деп қарай), ескіше уағыз оқып отырған қарт молда емес, заманауи және "
        f"түсінікті тілмен сөйлейтін адам. Адамның қазіргі өмірін түсін: жұмыс стресі, әлеуметтік "
        f"желі, достар арасындағы қысым — осыларды ескере отырып кеңес бер. "
        f"Ислами құндылықтарға сүйен: сабыр, тәуекел (Аллаһқа сенім арту), истиғфар арқылы жан тазалығы, "
        f"дұға мен намаздың күші, Аллаһтың Кешірімді әрі Мейірімді екенін еске сал — бірақ мұны "
        f"уағыз ретінде емес, жанашыр кеңес ретінде айт. "
        f"Құран аяттарының немесе хадистердің нақты нөмірлерін келтірме және дәл тұжырымдарды құрастырма — "
        f"жалған дереккөздерге сілтеме жасамай, жалпы ислами қағидалар туралы өз сөзіңмен айт. "
        f"Медициналық диагноз қойма, айыптамай, қорқытпай сөйле. Қазақ тілінде, қысқа (3-5 сөйлем) "
        f"жауап бер және қазір шыдай алмай қалмауға көмектесетін нақты практикалық қадаммен аяқта."
    )


async def ask_ai_coach(system_prompt: str, user_message: str) -> str | None:
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
        "max_tokens": 800,
        "temperature": 0.7,
    }
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


# ── Регистрация ───────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    db = SessionLocal()
    user = db.query(SobrietyUser).filter(SobrietyUser.telegram_id == chat_id).first()

    if user:
        await update.message.reply_text(
            f"Сәлем! Сен жүйеде тіркеулісің.\n\n"
            f"«{user.addiction}» жоқ — {user.streak} күн 🔥\n"
            f"Рекорд: {user.max_streak} күн\n\n"
            f"/status — прогресті көру\n"
            f"/relapse — шыдай алмағанымды белгілеу\n"
            f"/sos — қазір сырылғың келсе (ИИ-коуч кеңес береді)"
        )
        db.close()
        return

    db.close()
    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"register_{name}")]
        for name in ADDICTIONS
    ]
    await update.message.reply_text(
        "Сәлем! Мен сенің тәуелділіктен арылуыңа көмектесемін.\n\n"
        "Неден арылғың келеді?",
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
        await query.edit_message_text("Сен тіркеуден өткенсің ✅")
        db.close()
        return
    db.close()

    if addiction == "Басқа":
        context.user_data["awaiting_custom_addiction"] = True
        await query.edit_message_text("Неден арылғың келетінін мәтінмен жаз:")
        return

    create_sobriety_user(chat_id, addiction)
    context.user_data["awaiting_cost"] = True
    await query.edit_message_text(
        f"Дайын! Бүгіннен бастап «{addiction}»-ден бас тартуыңды бақылап отырамын. 🚀\n\n"
        f"Бұған күніне орта есеппен қанша жұмсайтын едің (теңгемен)?\n"
        f"Санын жаз — қанша теңге үнемдегеніңді көрсетіп отырамын. Санағыш келмесе — 0 деп жаз."
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
            f"Дайын! Бүгіннен бастап «{text}»-ден бас тартуыңды бақылап отырамын. 🚀\n\n"
            f"Бұған күніне орта есеппен қанша жұмсайтын едің (теңгемен)?\n"
            f"Санын жаз — қанша теңге үнемдегеніңді көрсетіп отырамын. Санағыш келмесе — 0 деп жаз."
        )
        return

    if context.user_data.get("awaiting_cost"):
        if not text.isdigit():
            await update.message.reply_text("Жай ғана сан жаз, мысалы 1500 (немесе 0).")
            return

        db = SessionLocal()
        user = db.query(SobrietyUser).filter(SobrietyUser.telegram_id == chat_id).first()
        if user:
            user.daily_cost = int(text)
            db.commit()
        db.close()

        context.user_data["awaiting_cost"] = False
        await update.message.reply_text(
            "Жазып алдым! 📊\n\n"
            "Әр таңда сағат 9:00-де қалай екеніңді сұрап отырамын.\n"
            "Командалар:\n"
            "/status — прогресс және үнемделген ақша\n"
            "/relapse — шыдай алмағанымды белгілеу\n"
            "/sos — қазір сырылғың келсе (ИИ-коуч кеңес береді)"
        )
        return

    # Свободный текст вне сценариев регистрации — ИИ здесь не отвечает, только /sos.
    await update.message.reply_text(
        "Сырылғың келсе — /sos жаз, ИИ-коуч кеңес береді.\nПрогресс үшін — /status."
    )


# ── Статус ────────────────────────────────────────────────────────────────

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    db = SessionLocal()
    user = db.query(SobrietyUser).filter(SobrietyUser.telegram_id == chat_id).first()
    if not user:
        await update.message.reply_text("Алдымен тіркелу керек: /start")
        db.close()
        return

    days_total = (date.today() - user.start_date).days
    text = (
        f"📊 «{user.addiction}» жоқ\n\n"
        f"🔥 Ағымдағы серия: {user.streak} күн\n"
        f"🏆 Рекорд: {user.max_streak} күн\n"
        f"📅 Жол басынан бергі барлығы: {days_total} күн"
    )
    if user.daily_cost:
        saved = user.streak * user.daily_cost
        text += f"\n💰 Үнемделді: {saved} теңге"
    await update.message.reply_text(text)
    db.close()


async def sos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    db = SessionLocal()
    user = db.query(SobrietyUser).filter(SobrietyUser.telegram_id == chat_id).first()
    db.close()

    addiction = user.addiction if user else "жаман әдет"
    ai_reply = await ask_ai_coach(
        coach_system_prompt(addiction),
        "Қазір шыдай алмай қалғым келіп тұр. Шыдауыма көмектес.",
    )
    await update.message.reply_text(ai_reply or random.choice(SOS_TIPS))


# ── Ежедневный чек-ин ─────────────────────────────────────────────────────

scheduler = AsyncIOScheduler()


@scheduler.scheduled_job("cron", hour=9, minute=0, timezone=TZ)
async def send_daily_checkin():
    db = SessionLocal()
    users = db.query(SobrietyUser).all()
    for user in users:
        keyboard = [[
            InlineKeyboardButton("✅ Шыдап жүрмін!", callback_data=f"holding_{user.id}"),
            InlineKeyboardButton("😔 Шыдай алмадым", callback_data=f"relapsed_{user.id}"),
        ]]
        await app.bot.send_message(
            chat_id=user.telegram_id,
            text=(
                f"Қайырлы таң! ☀️\n\n"
                f"🔥 «{user.addiction}» жоқ — {user.streak} күн\n"
                f"Кешегі күн қалай өтті?"
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
        await query.edit_message_text("Пайдаланушы табылмады. /start жаз")
        db.close()
        return

    today = date.today()

    if status_value == "holding":
        already = db.query(SobrietyCheckin).filter(
            SobrietyCheckin.user_id == user.id,
            SobrietyCheckin.date == today,
        ).first()
        if already:
            await query.edit_message_text("Сен бүгін белгілеп қойдың ✅")
            db.close()
            return

        db.add(SobrietyCheckin(user_id=user.id, date=today, status="holding"))
        user.streak += 1
        if user.streak > user.max_streak:
            user.max_streak = user.streak
        db.commit()

        quote = random.choice(MOTIVATIONAL_QUOTES)
        text = (
            f"Жарайсың! 🔥 «{user.addiction}» жоқ қазір {user.streak} күн!\n"
            f"Рекорд: {user.max_streak} күн"
        )
        if user.daily_cost:
            text += f"\n💰 Үнемделді: {user.streak * user.daily_cost} теңге"
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
        await query.edit_message_text("Бүгін шыдай алмадым деп бұрын белгіленген.")
        return

    db.add(SobrietyRelapse(user_id=user.id, date=today, note=None))
    user.streak = 0
    db.commit()
    await query.edit_message_text(
        "Шыдай алмадым деп жазылды. Берілме, ертең жаңа күн 💪\n"
        "Шыдай алмау — жолдың бір бөлігі, оның соңы емес."
    )


# ── Ручная отметка срыва командой ────────────────────────────────────────

async def relapse_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    db = SessionLocal()
    user = db.query(SobrietyUser).filter(SobrietyUser.telegram_id == chat_id).first()
    if not user:
        await update.message.reply_text("Алдымен тіркелу керек: /start")
        db.close()
        return

    keyboard = [[InlineKeyboardButton("😔 Иә, шыдай алмадым", callback_data=f"relapsed_{user.id}")]]
    await update.message.reply_text(
        "Сырылуды белгілегің келе ме? Серия нөлге түседі.",
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
