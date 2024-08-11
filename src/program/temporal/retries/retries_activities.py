import temporalio.activity
from program.temporal.orchestration import shared
from program.temporal.orchestration.workflows import start_media_item_workflow
from utils.logger import logger


@temporalio.activity.defn
async def obtain_and_retry_partial_mediaitems():
    from program.db.postgres_repository import PostgresRepository
    item_count = PostgresRepository.get_items_to_retry_count()
    logger.debug(f"Found {item_count} items to retry")
    if item_count == 0:
        return
    for page_number in range(0, (item_count // shared.NUMBER_OF_ROWS_PER_PAGE) + 1):
        items_to_submit = PostgresRepository.get_items_to_retry_for_page(shared.NUMBER_OF_ROWS_PER_PAGE, page_number)
        for item in items_to_submit:
            await start_media_item_workflow(item, "RetryLibrary")