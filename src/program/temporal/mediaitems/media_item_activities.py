from temporalio import activity
from program.media import MediaItem
from program.state_transition import process_event
from kink import di
from utils.logger import logger


@activity.defn
async def process_media_item_activity(existing_item: dict | None, started_by: str, item: dict) -> MediaItem:
    service = di[started_by]

    if existing_item:
        existing_item = MediaItem.from_dict(existing_item)

    if item:
        item = MediaItem.from_dict(item)

    while True:
        logger.info(f"Processing item {item.title} emitted by {service.__class__.__name__}")
        updated_item, next_service, items_to_submit = process_event(existing_item, service, item)

        if not next_service or not items_to_submit:
            logger.info(f"No further processing required for item {item.item_id}")
            break

        service = di[next_service.key]
        existing_item = updated_item if updated_item else item
        item = items_to_submit[0]

    return item


@activity.defn
async def get_media_item_from_db_activity(entity_id: int) -> MediaItem:
    try:
        from program.db.postgres_repository import PostgresRepository
        return PostgresRepository.get_media_item_by_id(entity_id)
    except Exception as e:
        logger.error(f"Error querying item with _id {id}: {e}")
        raise e


@activity.defn
async def store_media_item_activity(item: dict):
    try:
        item = MediaItem.from_dict(item)
        from program.db.postgres_repository import PostgresRepository
        PostgresRepository.update_item_in_db(item)
        logger.log("DATABASE", f"Item {item.item_id} stored in database.")
    except Exception as e:
        logger.error(f"Error storing item {item.item_id} with state {item.state.value}: {e}")
        raise e