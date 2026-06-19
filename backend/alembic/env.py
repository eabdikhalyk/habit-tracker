import os
import sys
from logging.config import fileConfig

from alembic import context

# --- Делаем наши модули (database, models) видимыми для Alembic ---
# env.py лежит в /app/alembic, а наши файлы — в /app. Добавляем /app в путь.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Переиспользуем УЖЕ настроенный engine из database.py (там обрабатывается
# postgres:// -> postgresql:// и SSL для Railway). Не дублируем логику подключения (DRY).
from database import Base, engine, DATABASE_URL   # noqa: E402
import models                                     # noqa: E402,F401 — регистрирует таблицы в Base.metadata

# Объект конфигурации Alembic (читает alembic.ini).
config = context.config

# Прокидываем обработанный URL в конфиг (нужно для offline-режима).
if DATABASE_URL:
    config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Настройка логирования из ini-файла.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# target_metadata — то, с чем Alembic СРАВНИВАЕТ реальную БД при autogenerate.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Генерация SQL без подключения к БД (режим --sql)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Применение миграций через готовый engine из database.py."""
    with engine.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()