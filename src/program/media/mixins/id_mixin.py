from pydantic import BaseModel
from sqlalchemy.orm import Mapped, mapped_column


class IdMixinSchema:
    id: Mapped[int] = mapped_column(primary_key=True, nullable=False)


class IdMixinModel(BaseModel):
    id: int = None
