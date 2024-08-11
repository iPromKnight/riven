import temporalio.activity
from kink import di
from program.content import Overseerr
from program.temporal.orchestration.workflows import start_media_item_workflow
from utils.logger import logger


@temporalio.activity.defn
async def scan_overseerr_requests():
    from program.media import MediaItem
    overseerr = di[Overseerr]
    logger.info("Scanning overseerr requests")
    for request in overseerr.run():
        if not isinstance(request, MediaItem):
            continue
        await start_media_item_workflow(request)
        logger.info(f"Started MediaItemWorkflow for item: {request.item_id}")
    logger.info("Overseerr scan completed.")