"""Trakt updater module"""

from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Generator, List, Optional, Union

from program.media.item import Episode, MediaItem, Movie, Season, Show
from program.settings.manager import settings_manager
from utils.logger import logger
from utils.request import get

CLIENT_ID = "0183a05ad97098d87287fe46da4ae286f434f32e8e951caad4cc147c947d79a3"


class TraktIndexer:
    """Trakt updater class"""
    key = "TraktIndexer"

    def __init__(self):
        self.key = "traktindexer"
        self.ids = []
        self.initialized = True
        self.settings = settings_manager.settings.indexer

    def copy_attributes(self, source, target):
        """Copy attributes from source to target."""
        attributes = ["file", "folder", "update_folder", "symlinked", "is_anime", "symlink_path", "subtitles"]
        for attr in attributes:
            target.set(attr, getattr(source, attr, None))

    def copy_items(self, itema: MediaItem, itemb: MediaItem):
        """Copy attributes from itema to itemb recursively."""
        if isinstance(itema, Show) and isinstance(itemb, Show):
            for seasona, seasonb in zip(itema.seasons, itemb.seasons):
                for episodea, episodeb in zip(seasona.episodes, seasonb.episodes):
                    self.copy_attributes(episodea, episodeb)
                seasonb.set("is_anime", itema.is_anime)
            itemb.set("is_anime", itema.is_anime)
        elif isinstance(itema, Movie) and isinstance(itemb, Movie):
            self.copy_attributes(itema, itemb)
        return itemb
            
    def run(self, in_item: MediaItem) -> Generator[Union[Movie, Show, Season, Episode], None, None]:
        """Run the Trakt indexer for the given item."""
        if not in_item:
            logger.error("Item is None")
            return
        if not (imdb_id := in_item.imdb_id):
            logger.error(f"Item {in_item.log_string} does not have an imdb_id, cannot index it")
            return
        
        item = create_item_from_imdb_id(imdb_id)

        if not isinstance(item, MediaItem):
            logger.error(f"Failed to get item from imdb_id: {imdb_id}")
            return
        if isinstance(item, Show):
            self._add_seasons_to_show(item, imdb_id)
        item = self.copy_items(in_item, item)
        item.indexed_at = datetime.now()
        yield item

    @staticmethod
    def should_submit(item: MediaItem) -> bool:
        if not item.indexed_at or not item.title:
            return True

        settings = settings_manager.settings.indexer

        try:
            interval = timedelta(seconds=settings.update_interval)
            return datetime.now() - item.indexed_at > interval
        except Exception:
            logger.error(f"Failed to parse date: {item.indexed_at} with format: {interval}")
            return False

    @staticmethod
    def _add_seasons_to_show(show: Show, imdb_id: str):
        """Add seasons to the given show using Trakt API."""
        if not isinstance(show, Show):
            logger.error(f"Item {show.log_string} is not a show")
            return

        if not imdb_id or not imdb_id.startswith("tt"):
            logger.error(f"Item {show.log_string} does not have an imdb_id, cannot index it")
            return

        seasons = get_show(imdb_id)
        for season in seasons:
            if season.number == 0:
                continue
            season_item = _map_item_from_data(season, "season", show.genres)
            if season_item:
                for episode in season.episodes:
                    episode_item = _map_item_from_data(episode, "episode", show.genres)
                    if episode_item:
                        season_item.add_episode(episode_item)
                show.add_season(season_item)


def _map_item_from_data(data, item_type: str, show_genres: List[str] = None) -> Optional[MediaItem]:
    """Map trakt.tv API data to MediaItemContainer."""
    if item_type not in ["movie", "show", "season", "episode"]:
        logger.debug(f"Unknown item type {item_type} for {data.title} not found in list of acceptable items")
        return None

    formatted_aired_at = _get_formatted_date(data, item_type)
    genres = getattr(data, "genres", None) or show_genres

    item = {
        "title": getattr(data, "title", None),
        "year": getattr(data, "year", None),
        "status": getattr(data, "status", None),
        "aired_at": formatted_aired_at,
        "imdb_id": getattr(data.ids, "imdb", None),
        "tvdb_id": getattr(data.ids, "tvdb", None),
        "tmdb_id": getattr(data.ids, "tmdb", None),
        "genres": genres,
        "network": getattr(data, "network", None),
        "country": getattr(data, "country", None),
        "language": getattr(data, "language", None),
        "requested_at": datetime.now(),
    }

    item["is_anime"] = (
        ("anime" in genres) 
        or ("animation" in genres and (item["country"] in ("jp", "kr")or item["language"] == "ja"))
        if genres
        else False
    )

    match item_type:
        case "movie":
            return Movie(item)
        case "show":
            return Show(item)
        case "season":
            item["number"] = data.number
            return Season(item)
        case "episode":
            item["number"] = data.number
            return Episode(item)
        case _:
            logger.error(f"Unknown item type {item_type} for {data.title} not found in list of acceptable items")
            return None


def _get_formatted_date(data, item_type: str) -> Optional[datetime]:
    """Get the formatted aired date from the data."""
    if item_type in ["show", "season", "episode"] and (first_aired := getattr(data, "first_aired", None)):
        return datetime.strptime(first_aired, "%Y-%m-%dT%H:%M:%S.%fZ")
    if item_type == "movie" and (released := getattr(data, "released", None)):
        return datetime.strptime(released, "%Y-%m-%d")
    return None


def get_show(imdb_id: str) -> dict:
    """Wrapper for trakt.tv API show method."""
    url = f"https://api.trakt.tv/shows/{imdb_id}/seasons?extended=episodes,full"
    response = get(url, additional_headers={"trakt-api-version": "2", "trakt-api-key": CLIENT_ID})
    return response.data if response.is_ok and response.data else {}


def create_item_from_imdb_id(imdb_id: str) -> Optional[MediaItem]:
    """Wrapper for trakt.tv API search method."""
    url = f"https://api.trakt.tv/search/imdb/{imdb_id}?extended=full"
    response = get(url, additional_headers={"trakt-api-version": "2", "trakt-api-key": CLIENT_ID})
    if not response.is_ok or not response.data:
        logger.error(f"Failed to create item using imdb id: {imdb_id}")  # This returns an empty list for response.data
        return None

    def find_first(preferred_types, data):
        for type in preferred_types:
            for d in data:
                if d.type == type:
                    return d
        return None

    data = next((d for d in response.data if d.type in ["show", "movie", "season"]), None)
    return _map_item_from_data(getattr(data, data.type), data.type) if data else None


def get_imdbid_from_tmdb(tmdb_id: str, type: str = "movie") -> Optional[str]:
    """Wrapper for trakt.tv API search method."""
    url = f"https://api.trakt.tv/search/tmdb/{tmdb_id}" # ?extended=full
    response = get(url, additional_headers={"trakt-api-version": "2", "trakt-api-key": CLIENT_ID})
    if not response.is_ok or not response.data:
        return None
    imdb_id = get_imdb_id_from_list(response.data, id_type="tmdb", _id=tmdb_id, type=type)
    if imdb_id and imdb_id.startswith("tt"):
        return imdb_id
    logger.error(f"Failed to fetch imdb_id for tmdb_id: {tmdb_id}")
    return None


def get_imdbid_from_tvdb(tvdb_id: str, type: str = "show") -> Optional[str]:
    """Wrapper for trakt.tv API search method."""
    url = f"https://api.trakt.tv/search/tvdb/{tvdb_id}"
    response = get(url, additional_headers={"trakt-api-version": "2", "trakt-api-key": CLIENT_ID})
    if not response.is_ok or not response.data:
        return None
    imdb_id = get_imdb_id_from_list(response.data, id_type="tvdb", _id=tvdb_id, type=type)
    if imdb_id and imdb_id.startswith("tt"):
        return imdb_id
    logger.error(f"Failed to fetch imdb_id for tvdb_id: {tvdb_id}")
    return None


def get_imdb_id_from_list(namespaces: List[SimpleNamespace], id_type: str = None, _id: str = None, type: str = None) -> Optional[str]:
    """Get the imdb_id from the list of namespaces."""
    if not any([id_type, _id, type]):
        return None

    for ns in namespaces:
        if type == "movie" and hasattr(ns, 'movie') and hasattr(ns.movie, 'ids') and hasattr(ns.movie.ids, 'imdb'):
            if str(getattr(ns.movie.ids, id_type)) == str(_id):
                return ns.movie.ids.imdb
        elif type == "show" and hasattr(ns, 'show') and hasattr(ns.show, 'ids') and hasattr(ns.show.ids, 'imdb'):
            if str(getattr(ns.show.ids, id_type)) == str(_id):
                return ns.show.ids.imdb
        elif type == "season" and hasattr(ns, 'season') and hasattr(ns.season, 'ids') and hasattr(ns.season.ids, 'imdb'):
            if str(getattr(ns.season.ids, id_type)) == str(_id):
                return ns.season.ids.imdb
        elif type == "episode" and hasattr(ns, 'episode') and hasattr(ns.episode, 'ids') and hasattr(ns.episode.ids, 'imdb'):
            if str(getattr(ns.episode.ids, id_type)) == str(_id):
                return ns.episode.ids.imdb
    return None