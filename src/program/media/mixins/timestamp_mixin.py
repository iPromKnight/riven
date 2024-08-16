from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import FunctionElement, DateTime
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Mapped, mapped_column


class utcnow(FunctionElement):
    type = DateTime()
    inherit_cache = True


@compiles(utcnow, "postgresql")
def pg_utcnow(element, compiler, **kw):
    return "TIMEZONE('utc', CURRENT_TIMESTAMP)"


class TimestampMixinSchema:
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=True,
        index=True,
        server_default=utcnow(),
        server_onupdate=utcnow(),
        sort_order=10000,
    )


class TimestampMixinModel(BaseModel):
    updated_at: datetime | None = None
