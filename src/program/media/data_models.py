from RTN import parse
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, TYPE_CHECKING

from program.media import States
from utils.logger import logger

if TYPE_CHECKING:
    from program.media import Season, Episode, Show, Movie, MediaItem


class StreamData(BaseModel):
    # Define fields here based on Stream's attributes
    pass


class MediaItemData(BaseModel):
    _id: int
    item_id: str
    number: Optional[int] = None
    type: str = "mediaitem"
    requested_at: datetime = Field(default_factory=datetime.now)
    requested_by: Optional[str] = None
    indexed_at: Optional[datetime] = None
    scraped_at: Optional[datetime] = None
    scraped_times: int = 0
    active_stream: Optional[Dict[str, str]] = Field(default_factory=dict)
    streams: List[StreamData] = Field(default_factory=list)
    blacklisted_streams: Optional[List[StreamData]] = None
    symlinked: bool = False
    symlinked_at: Optional[datetime] = None
    symlinked_times: int = 0
    file: Optional[str] = None
    folder: Optional[str] = None
    alternative_folder: Optional[str] = None
    is_anime: bool = False
    title: Optional[str] = None
    imdb_id: Optional[str] = None
    tvdb_id: Optional[str] = None
    tmdb_id: Optional[str] = None
    network: Optional[str] = None
    country: Optional[str] = None
    language: Optional[str] = None
    aired_at: Optional[datetime] = None
    year: Optional[int] = None
    genres: Optional[List[str]] = Field(default_factory=list)
    key: Optional[str] = None
    guid: Optional[str] = None
    update_folder: Optional[str] = None
    overseerr_id: Optional[int] = None
    last_state: Optional[str] = "Unknown"

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

    @property
    def is_released(self) -> bool:
        """Check if an item has been released."""
        if not self.aired_at:
            return False
        now = datetime.now()
        if self.aired_at > now:
            time_until_release = self.aired_at - now
            days, seconds = time_until_release.days, time_until_release.seconds
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            seconds = seconds % 60
            time_message = f"{self.log_string} will be released in {days} days, {hours:02}:{minutes:02}:{seconds:02}"
            logger.log("ITEM", time_message)
            return False
        return True

    @property
    def is_released_nolog(self):
        """Check if an item has been released."""
        if not self.aired_at:
            return False
        return True

    @property
    def state(self):
        return self._determine_state()

    @staticmethod
    def to_pydantic(data: Dict) -> "MediaItemData":
        type_map = {
            "movie": MovieData,
            "episode": EpisodeData,
            "season": SeasonData,
            "show": ShowData,
            "mediaitem": MediaItemData
        }
        model_type = data.get("type", "mediaitem").lower()
        model_class = type_map.get(model_type, MediaItemData)
        return model_class.model_validate(data)

    def to_sqlalchemy(self) -> "MediaItem":
        """Convert Pydantic model to corresponding SQLAlchemy model."""
        sqlalchemy_map = {
            "movie": Movie,
            "show": Show,
            "season": Season,
            "episode": Episode
        }

        sqlalchemy_class = sqlalchemy_map.get(self.type, MediaItem)
        return sqlalchemy_class(item=self.model_dump())

    def _determine_state(self):
        if self.key or self.update_folder == "updated":
            return States.Completed
        elif self.symlinked:
            return States.Symlinked
        elif self.file and self.folder:
            return States.Downloaded
        elif self.is_scraped():
            return States.Scraped
        elif self.title:
            return States.Indexed
        elif self.imdb_id and self.requested_by:
            return States.Requested
        return States.Unknown

    def store_state(self) -> None:
        self.last_state = self._determine_state().name

    def copy_other_media_attr(self, other):
        """Copy attributes from another media item."""
        self.title = getattr(other, "title", None)
        self.tvdb_id = getattr(other, "tvdb_id", None)
        self.tmdb_id = getattr(other, "tmdb_id", None)
        self.network = getattr(other, "network", None)
        self.country = getattr(other, "country", None)
        self.language = getattr(other, "language", None)
        self.aired_at = getattr(other, "aired_at", None)
        self.genres = getattr(other, "genres", [])
        self.is_anime = getattr(other, "is_anime", False)
        self.overseerr_id = getattr(other, "overseerr_id", None)

    def is_scraped(self):
        return (len(self.streams) > 0
                and
                all(stream.blacklisted == False for stream in self.streams))

    def to_dict(self):
        """Convert item to dictionary (API response)"""
        return {
            "item_id": str(self.item_id),
            "title": self.title,
            "type": self.__class__.__name__,
            "imdb_id": self.imdb_id if hasattr(self, "imdb_id") else None,
            "tvdb_id": self.tvdb_id if hasattr(self, "tvdb_id") else None,
            "tmdb_id": self.tmdb_id if hasattr(self, "tmdb_id") else None,
            "state": self.state.value,
            "imdb_link": self.imdb_link if hasattr(self, "imdb_link") else None,
            "aired_at": self.aired_at,
            "genres": self.genres if hasattr(self, "genres") else None,
            "is_anime": self.is_anime if hasattr(self, "is_anime") else False,
            "guid": self.guid,
            "requested_at": str(self.requested_at),
            "requested_by": self.requested_by,
            "scraped_at": self.scraped_at,
            "scraped_times": self.scraped_times,
        }

    def to_extended_dict(self, abbreviated_children=False):
        """Convert item to extended dictionary (API response)"""
        dict = self.to_dict()
        match self:
            case ShowData():
                dict["seasons"] = (
                    [season.to_extended_dict() for season in self.seasons]
                    if not abbreviated_children
                    else self.represent_children
                )
            case SeasonData():
                dict["episodes"] = (
                    [episode.to_extended_dict() for episode in self.episodes]
                    if not abbreviated_children
                    else self.represent_children
                )
        dict["language"] = self.language if hasattr(self, "language") else None
        dict["country"] = self.country if hasattr(self, "country") else None
        dict["network"] = self.network if hasattr(self, "network") else None
        dict["active_stream"] = (
            self.active_stream if hasattr(self, "active_stream") else None
        )
        dict["symlinked"] = self.symlinked if hasattr(self, "symlinked") else None
        dict["symlinked_at"] = (
            self.symlinked_at if hasattr(self, "symlinked_at") else None
        )
        dict["symlinked_times"] = (
            self.symlinked_times if hasattr(self, "symlinked_times") else None
        )
        dict["is_anime"] = self.is_anime if hasattr(self, "is_anime") else None
        dict["update_folder"] = (
            self.update_folder if hasattr(self, "update_folder") else None
        )
        dict["file"] = self.file if hasattr(self, "file") else None
        dict["folder"] = self.folder if hasattr(self, "folder") else None
        return dict

    def __iter__(self):
        for attr, _ in vars(self).items():
            yield attr

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self.imdb_id == other.imdb_id
        return False

    def copy(self, other):
        if other is None:
            return None
        self._id = getattr(other, "_id", None)
        self.imdb_id = getattr(other, "imdb_id", None)
        if hasattr(self, "number"):
            self.number = getattr(other, "number", None)
        return self

    def get(self, key, default=None):
        """Get item attribute"""
        return getattr(self, key, default)

    def set(self, key, value):
        """Set item attribute"""
        _set_nested_attr(self, key, value)

    def get_top_title(self) -> str:
        """Get the top title of the item."""
        match self.__class__.__name__:
            case "Season":
                return self.parent.title
            case "Episode":
                return self.parent.parent.title
            case _:
                return self.title

    def __hash__(self):
        return hash(self.item_id)

    @property
    def log_string(self):
        return self.title or self.imdb_id

    @property
    def collection(self):
        return self.parent.collection if self.parent else self.item_id


class MovieData(MediaItemData):
    def copy(self, other):
        super().copy(other)
        return self

    def __repr__(self):
        return f"Movie:{self.log_string}:{self.state.name}"

    def __hash__(self):
        return super().__hash__()

    def to_sqlalchemy(self) -> "Movie":
        from .item import Movie
        return Movie(item=self.model_dump())


class EpisodeData(MediaItemData):
    parent_id: Optional[int] = None
    parent: "SeasonData" = None

    def to_sqlalchemy(self) -> "Episode":
        from .item import Episode
        return Episode(item=self.model_dump())

    def __eq__(self, other):
        if (
                type(self) == type(other)
                and self.item_id == other.item_id
                and self.parent.parent.item_id == other.parent.parent.item_id
        ):
            return self.number == other.get("number", None)

    def __repr__(self):
        return f"Episode:{self.number}:{self.state.name}"

    def __hash__(self):
        return super().__hash__()

    def copy(self, other, copy_parent=True):
        super(EpisodeData, self).copy(other)
        if copy_parent and other.parent:
            self.parent = SeasonData.model_copy(other.parent, deep=True)
        return self

    def get_file_episodes(self) -> List[int]:
        if not self.file or not isinstance(self.file, str):
            raise ValueError("The file attribute must be a non-empty string.")
        # return list of episodes
        return parse(self.file).episode

    @property
    def log_string(self):
        return f"{self.parent.log_string}E{self.number:02}"

    def get_top_title(self) -> str:
        return self.parent.parent.title

    def get_top_year(self) -> Optional[int]:
        return self.parent.parent.year

    def get_season_year(self) -> Optional[int]:
        return self.parent.year


class SeasonData(MediaItemData):
    parent_id: Optional[int] = None
    parent: "ShowData" = None
    episodes: List[EpisodeData] = Field(default_factory=list)

    def to_sqlalchemy(self) -> "Season":
        from .item import Season
        data = self.model_dump()
        data["episodes"] = [episode.to_sqlalchemy() for episode in self.episodes]
        return Season(item=data)

    def _determine_state(self):
        if len(self.episodes) > 0:
            if all(episode.state == States.Completed for episode in self.episodes):
                return States.Completed
            if all(episode.state == States.Symlinked for episode in self.episodes):
                return States.Symlinked
            if all(episode.file and episode.folder for episode in self.episodes):
                return States.Downloaded
            if self.is_scraped():
                return States.Scraped
            if any(episode.state == States.Completed for episode in self.episodes):
                return States.PartiallyCompleted
            if any(episode.state == States.Indexed for episode in self.episodes):
                return States.Indexed
            if any(episode.state == States.Requested for episode in self.episodes):
                return States.Requested

        return States.Unknown

    @property
    def is_released(self) -> bool:
        return any(episode.is_released for episode in self.episodes)

    def store_state(self) -> None:
        for episode in self.episodes:
            episode.store_state()
        self.last_state = self._determine_state().name

    def __eq__(self, other):
        if (
                type(self) == type(other)
                and self.parent_id == other.parent_id
        ):
            return self.number == other.get("number", None)

    def __repr__(self):
        return f"Season:{self.number}:{self.state.name}"

    def __hash__(self):
        return super().__hash__()

    def copy(self, other, copy_parent=True):
        super(SeasonData, self).copy(other)
        for episode in other.episodes:
            new_episode = EpisodeData.model_copy(episode, deep=True)
            new_episode.parent = self
            self.episodes.append(new_episode)
        if copy_parent and other.parent:
            self.parent = ShowData.model_copy(other.parent, deep=True)
        return self

    def fill_in_missing_children(self, other):
        existing_episodes = [s.number for s in self.episodes]
        for e in other.episodes:
            if e.number not in existing_episodes:
                self.add_episode(e)

    def get_episode_index_by_id(self, item_id):
        """Find the index of an episode by its item_id."""
        for i, episode in enumerate(self.episodes):
            if episode.item_id == item_id:
                return i
        return None

    def represent_children(self):
        return [e.log_string for e in self.episodes]

    def add_episode(self, episode):
        """Add episode to season"""
        if episode.number in [e.number for e in self.episodes]:
            return

        episode.is_anime = self.is_anime
        self.episodes.append(episode)
        episode.parent = self
        self.episodes = sorted(self.episodes, key=lambda e: e.number)

    @property
    def log_string(self):
        return self.parent.log_string + " S" + str(self.number).zfill(2)

    def get_top_title(self) -> str:
        return self.parent.title


class ShowData(MediaItemData):
    seasons: List[SeasonData] = Field(default_factory=list)

    def to_sqlalchemy(self) -> "Show":
        from .item import Show
        data = self.model_dump()
        data["seasons"] = [season.to_sqlalchemy() for season in self.seasons]
        return Show(item=data)

    def get_season_index_by_id(self, item_id):
        """Find the index of an season by its item_id."""
        for i, season in enumerate(self.seasons):
            if season.item_id == item_id:
                return i
        return None

    def _determine_state(self):
        if all(season.state == States.Completed for season in self.seasons):
            return States.Completed
        if all(season.state == States.Symlinked for season in self.seasons):
            return States.Symlinked
        if all(season.state == States.Downloaded for season in self.seasons):
            return States.Downloaded
        if self.is_scraped():
            return States.Scraped
        if any(
                season.state in (States.Completed, States.PartiallyCompleted)
                for season in self.seasons
        ):
            return States.PartiallyCompleted
        if any(season.state == States.Indexed for season in self.seasons):
            return States.Indexed
        if any(season.state == States.Requested for season in self.seasons):
            return States.Requested
        return States.Unknown

    def store_state(self) -> None:
        for season in self.seasons:
            season.store_state()
        self.last_state = self._determine_state().name

    def __repr__(self):
        return f"Show:{self.log_string}:{self.state.name}"

    def __hash__(self):
        return super().__hash__()

    def copy(self, other):
        super(ShowData, self).copy(other)
        self.seasons = []
        for season in other.seasons:
            new_season = SeasonData.model_copy(season, deep=True)
            new_season.parent = self
            self.seasons.append(new_season)
        return self

    def fill_in_missing_children(self, other):
        existing_seasons = [s.number for s in self.seasons]
        for s in other.seasons:
            if s.number not in existing_seasons:
                self.add_season(s)
            else:
                existing_season = next(
                    es for es in self.seasons if s.number == es.number
                )
                existing_season.fill_in_missing_children(s)

    def add_season(self, season):
        """Add season to show"""
        if season.number not in [s.number for s in self.seasons]:
            season.is_anime = self.is_anime
            self.seasons.append(season)
            season.parent = self
            #season.item_id.parent_id = self.item_id
            self.seasons = sorted(self.seasons, key=lambda s: s.number)

    def propagate_attributes_to_childs(self):
        """Propagate show attributes to seasons and episodes if they are empty or do not match."""
        # Important attributes that need to be connected.
        attributes = ["genres", "country", "network", "language", "is_anime"]

        def propagate(target, source):
            for attr in attributes:
                source_value = getattr(source, attr, None)
                target_value = getattr(target, attr, None)
                # Check if the attribute source is not falsy (none, false, 0, [])
                # and if the target is not None we set the source to the target
                if (not target_value) and source_value is not None:
                    setattr(target, attr, source_value)

        for season in self.seasons:
            propagate(season, self)
            for episode in season.episodes:
                propagate(episode, self)


def _set_nested_attr(obj, key, value):
    if "." in key:
        parts = key.split(".", 1)
        current_key, rest_of_keys = parts[0], parts[1]

        if not hasattr(obj, current_key):
            raise AttributeError(f"Object does not have the attribute '{current_key}'.")

        current_obj = getattr(obj, current_key)
        _set_nested_attr(current_obj, rest_of_keys, value)
    elif isinstance(obj, dict):
        obj[key] = value
    else:
        setattr(obj, key, value)


def copy_item(item):
    """Copy an item"""
    if isinstance(item, MovieData):
        return MovieData.model_copy(item, deep=True)
    elif isinstance(item, ShowData):
        return ShowData.model_copy(item, deep=True)
    elif isinstance(item, SeasonData):
        return SeasonData.model_copy(item, deep=True)
    elif isinstance(item, EpisodeData):
        return EpisodeData.model_copy(item, deep=True)
    elif isinstance(item, MediaItemData):
        return MediaItemData.model_copy(item, deep=True)
    else:
        raise ValueError(f"Cannot copy item of type {type(item)}")