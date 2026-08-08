from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from app.core.config import DATABASE_URL
from app.core.database import Base
import app.db.models  # noqa: F401 - registers all models on Base.metadata

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Migrations always target the app's configured database, never the
# placeholder in alembic.ini - keeps a single source of truth for DATABASE_URL.
config.set_main_option("sqlalchemy.url", DATABASE_URL)

target_metadata = Base.metadata

# Opcje porównywania schematu, wspólne dla trybu online i offline - inaczej
# `alembic check` i `--autogenerate` mierzyłyby drift inną miarą w każdym z nich.
#
# compare_server_default: NIE jest domyślnie włączone, a bezpieczeństwo migracji
# d17abcef39ac stoi właśnie na server_default ('pl' dla istniejących kont).
# Bez tej opcji zniknięcie albo zmiana wartości domyślnej po stronie bazy nie
# zostałaby zgłoszona jako drift - a to jest dokładnie ta klasa rozjazdu, która
# nie boli, dopóki ktoś nie doda kolumny NOT NULL do tabeli z danymi.
#
# compare_type jest w Alembicu 1.19 domyślnie włączone; podane jawnie, żeby
# wersja biblioteki nie decydowała po cichu o zakresie kontroli.
COMPARISON_OPTIONS = {
    "compare_type": True,
    "compare_server_default": True,
}

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        **COMPARISON_OPTIONS,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            **COMPARISON_OPTIONS,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
