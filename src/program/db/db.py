import os

from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase

from program.settings.manager import settings_manager
from sqla_wrapper import Alembic, SQLAlchemy
from utils import data_dir_path
from utils.logger import logger

naming_convention = {
    "ix": "ix_ct_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_ct_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_ct_%(table_name)s_%(constraint_name)s",
    "fk": "fk_ct_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_ct_%(table_name)s",
}


class Base(DeclarativeBase, AsyncAttrs):
    metadata = MetaData(naming_convention=naming_convention)


db = SQLAlchemy(settings_manager.settings.database.host)

script_location = data_dir_path / "alembic/"


if not os.path.exists(script_location):
    os.makedirs(script_location)

alembic = Alembic(db, script_location)
alembic.init(script_location)


# https://stackoverflow.com/questions/61374525/how-do-i-check-if-alembic-migrations-need-to-be-generated
def need_upgrade_check() -> bool:
    """Check if there are any pending migrations."""
    with db.engine.connect() as connection:
        mc = MigrationContext.configure(connection)
        diff = compare_metadata(mc, db.Model.metadata)
    return bool(diff)


def run_migrations() -> None:
    """Run Alembic migrations if needed."""
    try:
        if need_upgrade_check():
            logger.info("New migrations detected, creating revision...")
            alembic.revision("auto-upg")
            logger.info("Applying migrations...")
            alembic.upgrade()
        else:
            logger.info("No new migrations detected.")
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        logger.info("Attempting to apply existing migrations...")
        alembic.upgrade()