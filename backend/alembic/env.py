import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# --- Делаем наши модули (database, models) видимыми для Alembic ---
# env.py лежит в /app/alembic, а наши файлы — в /app. Добавляем /app в путь.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Base   # noqa: E402  — наш declarative Base
import models               # noqa: E402,F401 — импорт регистрирует таблицы в Base.metadata

# Объект конфигурации Alembic (читает alembic.ini).
config = context.config

# Адрес БД берём из переменной окружения, а не из захардкоженного alembic.ini.
# Так один и тот же код работает и локально, и на проде (Railway) — отличается только env.
database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

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
    """Применение миграций с реальным подключением к БД."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()