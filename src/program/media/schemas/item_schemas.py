"""MediaItem class"""
from datetime import datetime
from typing import List, Optional
import sqlalchemy
from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from program.media.mixins import utcnow
from program.media.riven_base import RivenBaseSchema
from .subtitle_schemas import Subtitle
from .stream_schemas import Stream


class MediaItem(RivenBaseSchema):
    """MediaItem class"""
    item_id: Mapped[str] = mapped_column(sqlalchemy.String, nullable=False)
    number: Mapped[Optional[int]] = mapped_column(sqlalchemy.Integer, nullable=True)
    type: Mapped[str] = mapped_column(sqlalchemy.String, nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime, nullable=True, index=True, server_default=utcnow(),
                                                   server_onupdate=utcnow(), sort_order=9999)
    requested_by: Mapped[Optional[str]] = mapped_column(sqlalchemy.String, nullable=True)
    indexed_at: Mapped[Optional[datetime]] = mapped_column(sqlalchemy.DateTime, nullable=True)
    scraped_at: Mapped[Optional[datetime]] = mapped_column(sqlalchemy.DateTime, nullable=True)
    scraped_times: Mapped[Optional[int]] = mapped_column(sqlalchemy.Integer, default=0)
    active_stream: Mapped[Optional[dict[str]]] = mapped_column(sqlalchemy.JSON, nullable=True)
    streams: Mapped[list[Stream]] = relationship(secondary="StreamRelation", back_populates="parents")
    blacklisted_streams: Mapped[list[Stream]] = relationship(secondary="StreamBlacklistRelation",
                                                             back_populates="blacklisted_parents")
    symlinked: Mapped[Optional[bool]] = mapped_column(sqlalchemy.Boolean, default=False)
    symlinked_at: Mapped[Optional[datetime]] = mapped_column(sqlalchemy.DateTime, nullable=True)
    symlinked_times: Mapped[Optional[int]] = mapped_column(sqlalchemy.Integer, default=0)
    symlink_path: Mapped[Optional[str]] = mapped_column(sqlalchemy.String, nullable=True)
    file: Mapped[Optional[str]] = mapped_column(sqlalchemy.String, nullable=True)
    folder: Mapped[Optional[str]] = mapped_column(sqlalchemy.String, nullable=True)
    alternative_folder: Mapped[Optional[str]] = mapped_column(sqlalchemy.String, nullable=True)
    is_anime: Mapped[Optional[bool]] = mapped_column(sqlalchemy.Boolean, default=False)
    title: Mapped[Optional[str]] = mapped_column(sqlalchemy.String, nullable=True)
    imdb_id: Mapped[Optional[str]] = mapped_column(sqlalchemy.String, nullable=True)
    tvdb_id: Mapped[Optional[str]] = mapped_column(sqlalchemy.String, nullable=True)
    tmdb_id: Mapped[Optional[str]] = mapped_column(sqlalchemy.String, nullable=True)
    network: Mapped[Optional[str]] = mapped_column(sqlalchemy.String, nullable=True)
    country: Mapped[Optional[str]] = mapped_column(sqlalchemy.String, nullable=True)
    language: Mapped[Optional[str]] = mapped_column(sqlalchemy.String, nullable=True)
    aired_at: Mapped[Optional[datetime]] = mapped_column(sqlalchemy.DateTime, nullable=True)
    year: Mapped[Optional[int]] = mapped_column(sqlalchemy.Integer, nullable=True)
    genres: Mapped[Optional[List[str]]] = mapped_column(sqlalchemy.JSON, nullable=True)
    key: Mapped[Optional[str]] = mapped_column(sqlalchemy.String, nullable=True)
    guid: Mapped[Optional[str]] = mapped_column(sqlalchemy.String, nullable=True)
    update_folder: Mapped[Optional[str]] = mapped_column(sqlalchemy.String, nullable=True)
    overseerr_id: Mapped[Optional[int]] = mapped_column(sqlalchemy.Integer, nullable=True)
    last_state: Mapped[Optional[str]] = mapped_column(sqlalchemy.String, default="Unknown")
    subtitles: Mapped[list[Subtitle]] = relationship(Subtitle, back_populates="parent")

    __mapper_args__ = {
        "polymorphic_identity": "mediaitem",
        "polymorphic_on": "type",
        "with_polymorphic": "*",
    }


class Movie(MediaItem):
    """Movie class"""
    id: Mapped[int] = mapped_column(sqlalchemy.ForeignKey("MediaItem.id"), primary_key=True)
    __mapper_args__ = {
        "polymorphic_identity": "movie",
        "polymorphic_load": "inline",
    }


class Show(MediaItem):
    """Show class"""
    id: Mapped[int] = mapped_column(sqlalchemy.ForeignKey("MediaItem.id"), primary_key=True)
    seasons: Mapped[List["Season"]] = relationship(lazy=False, back_populates="parent", foreign_keys="Season.parent_id")

    __mapper_args__ = {
        "polymorphic_identity": "show",
        "polymorphic_load": "inline",
    }


class Season(MediaItem):
    """Season class"""
    id: Mapped[int] = mapped_column(sqlalchemy.ForeignKey("MediaItem.id"), primary_key=True)
    parent_id: Mapped[int] = mapped_column(sqlalchemy.ForeignKey("Show.id"), use_existing_column=True)
    parent: Mapped["Show"] = relationship(lazy=False, back_populates="seasons", foreign_keys="Season.parent_id")
    episodes: Mapped[List["Episode"]] = relationship(lazy=False, back_populates="parent",
                                                     foreign_keys="Episode.parent_id")
    __mapper_args__ = {
        "polymorphic_identity": "season",
        "polymorphic_load": "inline",
    }


class Episode(MediaItem):
    """Episode class"""
    id: Mapped[int] = mapped_column(sqlalchemy.ForeignKey("MediaItem.id"), primary_key=True)
    parent_id: Mapped[int] = mapped_column(sqlalchemy.ForeignKey("Season.id"), use_existing_column=True)
    parent: Mapped["Season"] = relationship(lazy=False, back_populates="episodes", foreign_keys="Episode.parent_id")

    __mapper_args__ = {
        "polymorphic_identity": "episode",
        "polymorphic_load": "inline",
    }
