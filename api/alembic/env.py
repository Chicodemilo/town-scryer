"""Alembic environment configuration.

Imports the Flask app's SQLAlchemy models and DATABASE_URL so that
autogenerate can diff against the live schema.
"""
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Ensure the api/ directory is on sys.path so 'app' is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app, db
from app.models.user import User
from app.models.terms_content import TermsContent
from app.models.page_hit import PageHit

# Alembic Config object
config = context.config

# Set up Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Create the Flask app to load config (including DATABASE_URL)
flask_app = create_app()

# Override sqlalchemy.url with the app's DATABASE_URL
config.set_main_option("sqlalchemy.url", flask_app.config["SQLALCHEMY_DATABASE_URI"])

# Target metadata for autogenerate
target_metadata = db.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — emit SQL without a live connection."""
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
    """Run migrations in 'online' mode — connect to the database."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
