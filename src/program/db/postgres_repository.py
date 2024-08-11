import os
import shutil
import alembic
from kink import di
from rapidfuzz.distance import Levenshtein
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import joinedload
from utils.logger import logger
from utils import alembic_dir
from .db import db, alembic


class PostgresRepository:
    @staticmethod
    def get_media_item_stats():
        from program.media import Movie, Show, Season, Episode, MediaItem, States
        with db.Session() as session:
            movies_symlinks = session.execute(select(func.count(Movie._id)).where(Movie.symlinked == True)).scalar_one()
            episodes_symlinks = session.execute(
                select(func.count(Episode._id)).where(Episode.symlinked == True)).scalar_one()
            total_symlinks = movies_symlinks + episodes_symlinks
            total_movies = session.execute(select(func.count(Movie._id))).scalar_one()
            total_shows = session.execute(select(func.count(Show._id))).scalar_one()
            total_seasons = session.execute(select(func.count(Season._id))).scalar_one()
            total_episodes = session.execute(select(func.count(Episode._id))).scalar_one()
            total_items = session.execute(select(func.count(MediaItem._id))).scalar_one()
            _incomplete_items = session.execute(select(MediaItem).where(MediaItem.last_state != "Completed")).unique().scalars().all()

            incomplete_retries = {}
            for item in _incomplete_items:
                incomplete_retries[item.log_string] = item.scraped_times

            states = {}
            for state in States:
                states[state] = session.execute(
                    select(func.count(MediaItem._id)).where(MediaItem.last_state == state.value)).scalar_one()
            session.expunge_all()
            session.close()
            incomplete_items = len(_incomplete_items)
            return total_items, total_movies, total_shows, total_seasons, total_episodes, total_symlinks, incomplete_items, incomplete_retries, states

    @staticmethod
    def get_items_to_retry_count():
        from program.media import MediaItem
        with db.Session() as session:
            count = session.execute(
                select(func.count(MediaItem._id))
                .where(MediaItem.type.in_(["movie", "show"]))
                .where(MediaItem.last_state != "Completed")
            ).scalar_one()
            return count

    @staticmethod
    def get_items_to_retry_for_page(number_of_rows_per_page: int, page_number: int):
        from program.media import MediaItem
        with db.Session() as session:
            items_to_submit = session.execute(
                select(MediaItem)
                .where(MediaItem.type.in_(["movie", "show"]))
                .where(MediaItem.last_state != "Completed")
                .order_by(MediaItem.requested_at.desc())
                .limit(number_of_rows_per_page)
                .offset(page_number * number_of_rows_per_page)
                .options(joinedload("*"))
            ).unique().scalars().all()
            session.expunge_all()
            session.close()
            return items_to_submit

    @staticmethod
    def update_item_in_db(item):
        with db.Session() as session:
            item.store_state()
            session.merge(item)
            session.commit()
            session.close()

    @staticmethod
    def get_media_item_by_id(id: int):
        from program.media import MediaItem
        with (db.Session() as session):
            item = session.execute(
                select(MediaItem)
                .where(MediaItem._id == id)
            ).unique().scalar_one_or_none()
            if item:
                session.expunge(item)
                session.close()
                return item
            return None

    @staticmethod
    def get_items(limit, page, type, state, sort, search):
        from program.media import MediaItem, States
        query = select(MediaItem)

        if search:
            search_lower = search.lower()
            if search_lower.startswith("tt"):
                query = query.where(MediaItem.imdb_id == search_lower)
            else:
                query = query.where(
                    (func.lower(MediaItem.title).like(f"%{search_lower}%")) |
                    (func.lower(MediaItem.imdb_id).like(f"%{search_lower}%"))
                )

        if state:
            filter_lower = state.lower()
            filter_state = None
            for state_enum in States:
                if Levenshtein.distance(filter_lower, state_enum.name.lower()) <= 0.82:
                    filter_state = state_enum
                    break
            if filter_state:
                query = query.where(MediaItem.state == filter_state)
            else:
                valid_states = [state_enum.name for state_enum in States]
                raise ValueError(f"Invalid filter state: {state}. Valid states are: {valid_states}")

        if type:
            if "," in type:
                types = type.split(",")
                for type in types:
                    if type not in ["movie", "show", "season", "episode"]:
                        raise ValueError(f"Invalid type: {type}. Valid types are: ['movie', 'show', 'season', 'episode']")
                query = query.where(MediaItem.type.in_(types))

        if sort and not search:
            if sort.lower() == "asc":
                query = query.order_by(MediaItem.requested_at.asc())
            elif sort.lower() == "desc":
                query = query.order_by(MediaItem.requested_at.desc())
            else:
                raise ValueError(f"Invalid sort: {sort}. Valid sorts are: ['asc', 'desc']")

        with db.Session() as session:
            total_items = session.execute(select(func.count()).select_from(query.subquery())).scalar_one()
            items = session.execute(query.offset((page - 1) * limit).limit(limit)).unique().scalars().all()
            total_pages = (total_items + limit - 1) // limit
            return {
                "success": True,
                "items": items,
                "page": page,
                "limit": limit,
                "total_items": total_items,
                "total_pages": total_pages,
            }

    @staticmethod
    def get_media_item_by_imdb_id(imdb_id: str, season=None, episode=None):
        from program.media import MediaItem, Episode, Season
        with db.Session() as session:
            if season is not None and episode is not None:
                item = session.execute(
                    select(Episode).where(
                        (Episode.imdb_id == imdb_id) &
                        (Episode.season_number == season) &
                        (Episode.episode_number == episode)
                    )
                ).scalar_one_or_none()
            elif season is not None:
                item = session.execute(
                    select(Season).where(
                        (Season.imdb_id == imdb_id) &
                        (Season.season_number == season)
                    )
                ).scalar_one_or_none()
            else:
                item = session.execute(
                    select(MediaItem).where(MediaItem.imdb_id == imdb_id)
                    .options(joinedload("*"))
                ).unique().scalar_one_or_none()
            if item:
                session.expunge(item)
                session.close()
                return item
            return None

    @staticmethod
    def remove_item_by_imdb_id(imdb_id: str) -> bool:
        from program.media import MediaItem, Episode, Season, Movie, Show
        from program.media.stream import Stream
        try:
            with (db.Session() as session):
                item = session.execute(
                    select(MediaItem)
                    .where(MediaItem.imdb_id == imdb_id)
                ).unique().scalar_one_or_none()
                if not item:
                    return False

                item_type = None
                if item.type == "movie":
                    item_type = Movie
                elif item.type == "show":
                    item_type = Show
                elif item.type == "season":
                    item_type = Season
                elif item.type == "episode":
                    item_type = Episode

                if item_type:
                    session.execute(delete(Stream).where(Stream.parent_id == item._id))
                    session.execute(delete(item_type).where(item_type._id == item._id))
                    session.execute(delete(MediaItem.__table__).where(MediaItem._id == item._id))
                    session.commit()
                    return True
                return False
        except Exception as e:
            logger.error("Failed to remove item from imdb_id, " + str(e))
            return False

    @staticmethod
    def process_meta_data():
        from program.media import MediaItem, Episode, Season, Movie, Show
        with db.Session() as session:
            res = session.execute(select(func.count(MediaItem._id))).scalar_one()
            added = []
            if res == 0:
                for item in di["SymlinkLibrary"].run():
                    if di["SettingsManager"].settings.map_metadata:
                        if isinstance(item, (Movie, Show)):
                            try:
                                item = next(di["TraktIndexer"].run(item))
                            except StopIteration as e:
                                logger.error(f"Failed to enhance metadata for {item.title} ({item.item_id}): {e}")
                                continue
                            if item.item_id in added:
                                logger.error(f"Cannot enhance metadata, {item.title} ({item.item_id}) contains multiple folders. Manual resolution required. Skipping.")
                                continue
                            added.append(item.item_id)
                            item.store_state()
                            session.add(item)
                            logger.debug(f"Mapped metadata to {item.type.title()}: {item.log_string}")
                session.commit()
            movies_symlinks = session.execute(select(func.count(Movie._id)).where(Movie.symlinked == True)).scalar_one() # noqa
            episodes_symlinks = session.execute(select(func.count(Episode._id)).where(Episode.symlinked == True)).scalar_one() # noqa
            total_symlinks = movies_symlinks + episodes_symlinks
            total_movies = session.execute(select(func.count(Movie._id))).scalar_one()
            total_shows = session.execute(select(func.count(Show._id))).scalar_one()
            total_seasons = session.execute(select(func.count(Season._id))).scalar_one()
            total_episodes = session.execute(select(func.count(Episode._id))).scalar_one()
            total_items = session.execute(select(func.count(MediaItem._id))).scalar_one()
            logger.log("ITEM", f"Movies: {total_movies} (Symlinks: {movies_symlinks})")
            logger.log("ITEM", f"Shows: {total_shows}")
            logger.log("ITEM", f"Seasons: {total_seasons}")
            logger.log("ITEM", f"Episodes: {total_episodes} (Symlinks: {episodes_symlinks})")
            logger.log("ITEM", f"Total Items: {total_items} (Symlinks: {total_symlinks})")

    @staticmethod
    def hard_reset_database():
        """Resets the database to a fresh state."""
        logger.log("DATABASE", "Resetting Database")

        # Drop all tables
        db.Model.metadata.drop_all(db.engine)
        logger.log("DATABASE", "All MediaItem tables dropped")

        # Drop the alembic_version table
        with db.engine.connect() as connection:
            connection.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))
        logger.log("DATABASE", "Alembic table dropped")

        # Recreate all tables
        db.Model.metadata.create_all(db.engine)
        logger.log("DATABASE", "All tables recreated")

        # Reinitialize Alembic
        logger.log("DATABASE", "Removing Alembic Directory")
        shutil.rmtree(alembic_dir, ignore_errors=True)
        os.makedirs(alembic_dir, exist_ok=True)
        alembic.init(alembic_dir)
        logger.log("DATABASE", "Alembic reinitialized")

        logger.log("DATABASE", "Hard Reset Complete")

    reset = os.getenv("HARD_RESET", None)
    if reset is not None and reset.lower() in ["true", "1"]:
        hard_reset_database()