FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# При старте: сначала применяем миграции (alembic), затем запускаем бота.
# Так прод-БД всегда догоняется до актуальной схемы при каждом деплое.
CMD ["sh", "-c", "alembic upgrade head && python bot.py"]