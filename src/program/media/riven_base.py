from typing import TypeAlias
from pydantic import BaseModel
from sqlalchemy.orm import as_declarative

from program.db.db import Base
from program.media.mixins import IdMixinModel, TimestampMixinModel, TablesMixinSchema, IdMixinSchema, TimestampMixinSchema

RivenDbModel: TypeAlias = BaseModel
RivenDbSchema: TypeAlias = Base


class RivenBaseModel(RivenDbModel, IdMixinModel, TimestampMixinModel):
    """Base model for RivenDB models."""
    pass


@as_declarative()
class RivenBaseSchema(RivenDbSchema, IdMixinSchema, TimestampMixinSchema, TablesMixinSchema):
    """Base schema for RivenDB schemas."""
    pass
