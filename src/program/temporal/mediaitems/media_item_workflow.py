from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError
from utils.logger import logger
from program.media import MediaItem
from program.temporal.orchestration import shared
from program.temporal.mediaitems import (
    process_media_item_activity,
    store_media_item_activity,
    get_media_item_from_db_activity
)

ACTIVITY_EXECUTION_TIMEOUT = timedelta(minutes=2)
ACTIVITY_RETRY_POLICY = RetryPolicy(maximum_attempts=1)


@workflow.defn(name=shared.MEDIA_ITEM_WORKFLOW, sandboxed=False)
class MediaItemWorkflow:
    item: MediaItem
    started_by: str
    existing_item: MediaItem | None

    @workflow.run
    async def run(self, item: dict, started_by: str):
        self.item = MediaItem.from_dict(item)
        self.existing_item = None
        self.started_by = started_by
        logger.info(f"Running MediaItemWorkflow for item: {self.item.item_id}, emitted by service: {self.started_by}")

        try:
            await self.__get_existing_item()
            await self.__run_process_queue()
            await self.__store_item()
            return {"status": "success", "state": self.item.state.value}
        except Exception as e:
            raise ApplicationError(f"Error running MediaItemWorkflow: {e}")

    async def __get_existing_item(self):
        if self.item._id:
            logger.log("DATABASE", f"Getting existing item from database with id: {self.item._id}")
            self.existing_item = await workflow.execute_local_activity(
                get_media_item_from_db_activity,
                arg=self.item._id,
                start_to_close_timeout=ACTIVITY_EXECUTION_TIMEOUT,
                retry_policy=ACTIVITY_RETRY_POLICY
            )

    async def __run_process_queue(self):
        existing_item = self.existing_item
        if existing_item:
            existing_item = existing_item.to_temporal_dict()
        item = self.item.to_temporal_dict()

        self.item = await workflow.execute_local_activity(
            process_media_item_activity,
            args=[existing_item, self.started_by, item],
            start_to_close_timeout=ACTIVITY_EXECUTION_TIMEOUT,
            retry_policy=ACTIVITY_RETRY_POLICY
        )

    async def __store_item(self):
        await workflow.execute_local_activity(
            store_media_item_activity,
            arg=self.item.to_temporal_dict(),
            start_to_close_timeout=ACTIVITY_EXECUTION_TIMEOUT,
            retry_policy=ACTIVITY_RETRY_POLICY
        )