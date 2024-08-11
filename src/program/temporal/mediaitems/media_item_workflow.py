from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

from program.media import MediaItem
from program.temporal.mediaitems import (
    handle_requested_or_unknown_state,
    handle_indexed_or_partially_completed_state,
    handle_scraped_state,
    handle_downloaded_state,
    handle_symlinked_state,
    handle_completed_state, store_item
)
from program.media import States
from program.temporal.orchestration import shared
from utils.logger import logger

ACTIVITY_EXECUTION_TIMEOUT = timedelta(minutes=2)
ACTIVITY_RETRY_POLICY = RetryPolicy(maximum_attempts=1)


@workflow.defn(name=shared.MEDIA_ITEM_WORKFLOW, sandboxed=False)
class MediaItemWorkflow:
    item: MediaItem

    @workflow.run
    async def run(self, item: MediaItem):
        self.item = item
        logger.info(f"Running MediaItemWorkflow for item: {self.item.item_id}")
        try:
            if self.item.state == States.Requested:
                self.item = await self.execute_local_activity(handle_requested_or_unknown_state)

            if self.item.state == States.Indexed:
                self.item = await self.execute_local_activity(handle_indexed_or_partially_completed_state)

            if self.item.state == States.Scraped:
                self.item = await self.execute_local_activity(handle_scraped_state)

            if self.item.state == States.Downloaded:
                self.item = await self.execute_local_activity(handle_downloaded_state)

            if self.item.state == States.Symlinked:
                self.item = await self.execute_local_activity(handle_symlinked_state)

            if self.item.state == States.Completed:
                self.item = await self.execute_local_activity(handle_completed_state)

            await self.execute_local_activity(store_item)
            return {"status": "success", "state": self.item.state.value}
        except Exception as e:
            raise ApplicationError(f"Error running MediaItemWorkflow: {e}")

    async def execute_local_activity(self, activity_func):
        return await workflow.execute_activity(
            activity=activity_func,
            arg=self.item,
            start_to_close_timeout=ACTIVITY_EXECUTION_TIMEOUT,
            retry_policy=ACTIVITY_RETRY_POLICY)