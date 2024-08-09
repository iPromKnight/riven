"""MediaItem class"""
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

import sqlalchemy

from program.db.db import db
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .stream import Stream

if TYPE_CHECKING:
    from .data_models import MediaItemData, MovieData, ShowData, SeasonData, EpisodeData


class MediaItem(db.Model):
    """MediaItem class"""
    __tablename__ = "MediaItem"
    _id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[str] = mapped_column(sqlalchemy.String, nullable=False)
    number: Mapped[Optional[int]] = mapped_column(sqlalchemy.Integer, nullable=True)
    type: Mapped[str] = mapped_column(sqlalchemy.String, nullable=False)
    requested_at: Mapped[Optional[datetime]] = mapped_column(sqlalchemy.DateTime, default=datetime.now())
    requested_by: Mapped[Optional[str]] = mapped_column(sqlalchemy.String, nullable=True)
    indexed_at: Mapped[Optional[datetime]] = mapped_column(sqlalchemy.DateTime, nullable=True)
    scraped_at: Mapped[Optional[datetime]] = mapped_column(sqlalchemy.DateTime, nullable=True)
    scraped_times: Mapped[Optional[int]] = mapped_column(sqlalchemy.Integer, default=0)
    active_stream: Mapped[Optional[dict[str, str]]] = mapped_column(sqlalchemy.JSON, nullable=True)
    streams: Mapped[List[Stream]] = relationship("Stream", back_populates='parent', lazy="select",
                                                 cascade="all, delete-orphan")
    blacklisted_streams: Mapped[Optional[List[Stream]]] = mapped_column(sqlalchemy.JSON, nullable=True)
    symlinked: Mapped[Optional[bool]] = mapped_column(sqlalchemy.Boolean, default=False)
    symlinked_at: Mapped[Optional[datetime]] = mapped_column(sqlalchemy.DateTime, nullable=True)
    symlinked_times: Mapped[Optional[int]] = mapped_column(sqlalchemy.Integer, default=0)
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

    __mapper_args__ = {
        "polymorphic_identity": "mediaitem",
        "polymorphic_on": "type",
        "with_polymorphic": "*",
    }

    def __init__(self, item: dict) -> None:
        self.requested_at = item.get("requested_at", datetime.now())
        self.requested_by = item.get("requested_by")

        self.indexed_at = None

        self.scraped_at = None
        self.scraped_times = 0
        self.active_stream = item.get("active_stream", {})
        self.streams: List[Stream] = []

        self.symlinked = False
        self.symlinked_at = None
        self.symlinked_times = 0

        self.file = None
        self.folder = None
        self.is_anime = item.get("is_anime", False)

        # Media related
        self.title = item.get("title")
        self.imdb_id = item.get("imdb_id")
        if self.imdb_id:
            self.imdb_link = f"https://www.imdb.com/title/{self.imdb_id}/"
            if not hasattr(self, "item_id"):
                self.item_id = self.imdb_id
        self.tvdb_id = item.get("tvdb_id")
        self.tmdb_id = item.get("tmdb_id")
        self.network = item.get("network")
        self.country = item.get("country")
        self.language = item.get("language")
        self.aired_at = item.get("aired_at")
        self.year = item.get("year")
        self.genres = item.get("genres", [])

        # Plex related
        self.key = item.get("key")
        self.guid = item.get("guid")
        self.update_folder = item.get("update_folder")

        # Overseerr related
        self.overseerr_id = item.get("overseerr_id")

    def to_pydantic(self) -> "MediaItemData":
        from .data_models import MediaItemData, MovieData, ShowData, SeasonData, EpisodeData
        pydantic_map = {
            "movie": MovieData,
            "show": ShowData,
            "season": SeasonData,
            "episode": EpisodeData
        }
        model_dict = {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        pydantic_class = pydantic_map.get(self.type, MediaItemData)
        return pydantic_class(**model_dict)


class Movie(MediaItem):
    """Movie class"""
    __tablename__ = "Movie"
    _id: Mapped[int] = mapped_column(sqlalchemy.ForeignKey("MediaItem._id"), primary_key=True)
    __mapper_args__ = {
        "polymorphic_identity": "movie",
        "polymorphic_load": "inline",
    }

    def __init__(self, item):
        self.type = "movie"
        self.file = item.get("file", None)
        super().__init__(item)
        self.item_id = self.imdb_id

    def to_pydantic(self) -> "MovieData":
        from .data_models import MovieData
        model_dict = {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        return MovieData(**model_dict)


class Show(MediaItem):
    """Show class"""
    __tablename__ = "Show"
    _id: Mapped[int] = mapped_column(sqlalchemy.ForeignKey("MediaItem._id"), primary_key=True)
    seasons: Mapped[List["Season"]] = relationship(lazy=False, back_populates="parent", foreign_keys="Season.parent_id")

    __mapper_args__ = {
        "polymorphic_identity": "show",
        "polymorphic_load": "inline",
    }

    def __init__(self, item):
        super().__init__(item)
        self.type = "show"
        self.locations = item.get("locations", [])
        self.seasons: list[Season] = item.get("seasons", [])
        self.item_id = item.get("imdb_id")
        self.propagate_attributes_to_childs()

    def to_pydantic(self) -> "ShowData":
        from .data_models import ShowData
        model_dict = {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        model_dict["seasons"] = [season.to_pydantic() for season in self.seasons]
        return ShowData(**model_dict)


class Season(MediaItem):
    """Season class"""
    __tablename__ = "Season"
    _id: Mapped[int] = mapped_column(sqlalchemy.ForeignKey("MediaItem._id"), primary_key=True)
    parent_id: Mapped[int] = mapped_column(sqlalchemy.ForeignKey("Show._id"), use_existing_column=True)
    parent: Mapped["Show"] = relationship(lazy=False, back_populates="seasons", foreign_keys="Season.parent_id")
    episodes: Mapped[List["Episode"]] = relationship(lazy=False, back_populates="parent",
                                                     foreign_keys="Episode.parent_id")
    __mapper_args__ = {
        "polymorphic_identity": "season",
        "polymorphic_load": "inline",
    }

    def __init__(self, item):
        self.type = "season"
        self.number = item.get("number", None)
        self.episodes: list[Episode] = item.get("episodes", [])
        self.item_id = self.number
        self.parent = item.get("parent", None)
        super().__init__(item)
        if self.parent and isinstance(self.parent, Show):
            self.is_anime = self.parent.is_anime

    def to_pydantic(self) -> "SeasonData":
        from .data_models import SeasonData
        model_dict = {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        model_dict["episodes"] = [episode.to_pydantic() for episode in self.episodes]
        return SeasonData(**model_dict)


class Episode(MediaItem):
    """Episode class"""
    __tablename__ = "Episode"
    _id: Mapped[int] = mapped_column(sqlalchemy.ForeignKey("MediaItem._id"), primary_key=True)
    parent_id: Mapped[int] = mapped_column(sqlalchemy.ForeignKey("Season._id"), use_existing_column=True)
    parent: Mapped["Season"] = relationship(lazy=False, back_populates="episodes", foreign_keys="Episode.parent_id")

    __mapper_args__ = {
        "polymorphic_identity": "episode",
        "polymorphic_load": "inline",
    }

    def __init__(self, item):
        self.type = "episode"
        self.number = item.get("number", None)
        self.file = item.get("file", None)
        self.item_id = self.number  # , parent_id=item.get("parent_id"))
        super().__init__(item)
        if self.parent and isinstance(self.parent, Season):
            self.is_anime = self.parent.parent.is_anime

    def to_pydantic(self) -> "EpisodeData":
        from .data_models import EpisodeData
        model_dict = {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        return EpisodeData(**model_dict)