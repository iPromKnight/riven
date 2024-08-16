from program.db.db import db
import sqlalchemy
from sqlalchemy.orm import Mapped, mapped_column, relationship

from program.media.riven_base import RivenBaseSchema


class StreamRelation(RivenBaseSchema):
    parent_id: Mapped[int] = mapped_column(sqlalchemy.Integer,
                                           sqlalchemy.ForeignKey("MediaItem.id", ondelete="CASCADE"))
    child_id: Mapped[int] = mapped_column(sqlalchemy.Integer, sqlalchemy.ForeignKey("Stream.id", ondelete="CASCADE"))


class StreamBlacklistRelation(db.Model):
    media_item_id: Mapped[int] = mapped_column(sqlalchemy.Integer,
                                               sqlalchemy.ForeignKey("MediaItem.id", ondelete="CASCADE"))
    stream_id: Mapped[int] = mapped_column(sqlalchemy.Integer, sqlalchemy.ForeignKey("Stream.id", ondelete="CASCADE"))


class Stream(db.Model):
    infohash: Mapped[str] = mapped_column(sqlalchemy.String, nullable=False)
    raw_title: Mapped[str] = mapped_column(sqlalchemy.String, nullable=False)
    parsed_title: Mapped[str] = mapped_column(sqlalchemy.String, nullable=False)
    rank: Mapped[int] = mapped_column(sqlalchemy.Integer, nullable=False)
    lev_ratio: Mapped[float] = mapped_column(sqlalchemy.Float, nullable=False)

    parents: Mapped[list["MediaItem"]] = relationship(secondary="StreamRelation", back_populates="streams")
    blacklisted_parents: Mapped[list["MediaItem"]] = relationship(secondary="StreamBlacklistRelation",
                                                                  back_populates="blacklisted_streams")