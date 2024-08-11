from temporalio import activity
from program.media import MediaItem, Movie, Show, Season, Episode
from program.state_transition import process_event
from utils.logger import logger


@activity.defn
async def process_media_item_activity(existing_item: dict | None, started_by: str, item: dict) -> dict:
    service = started_by

    if existing_item:
        existing_item = MediaItem.from_dict(existing_item)

    if item:
        item = MediaItem.from_dict(item)

    while True:
        if item and service:
            if service == "TraktIndexer":
                logger.log("NEW", f"Handling submission from {service} with {item.log_identifier()}")
            else:
                logger.log("PROGRAM", f"Handling submission from {service} with {item.log_identifier()}")
        else:
            logger.error(f"Submission service or item is None: {service}, {item}")
            break

        updated_item, next_service, items_to_submit = process_event(existing_item, service, item)

        if not next_service or not items_to_submit:
            break

        service = next_service
        # todo: Prom: This is where we'll implement recursive handling of items for seasons and episodes.
        existing_item = updated_item if updated_item else item
        item = items_to_submit[0]

    return item.to_temporal_dict()


@activity.defn
async def get_media_item_from_db_activity(imdb_id: str) -> dict | None:
    try:
        from program.db.postgres_repository import PostgresRepository
        item = PostgresRepository.get_media_item_by_imdb_id(imdb_id)
        if not item:
            logger.log("DATABASE", f"No item found with id '{imdb_id}'. Item must be new.")
            return None
        logger.log("DATABASE", f"Item with id '{imdb_id}' found in database, returning {item.log_identifier()}")
        return item.to_temporal_dict()
    except Exception as e:
        logger.error(f"Error querying item with _id {id}: {e}")
        raise e


@activity.defn
async def store_media_item_activity(item: dict):
    try:
        item = MediaItem.from_dict(item)
        from program.db.postgres_repository import PostgresRepository
        PostgresRepository.update_item_in_db(item)
        logger.log("DATABASE", f"{item.log_identifier()} stored in database.")
    except Exception as e:
        logger.error(f"Error storing item {item.item_id} with state {item.state.value}: {e}")
        raise e