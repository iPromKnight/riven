from datetime import timedelta
from temporalio.common import RetryPolicy
from temporalio import workflow
from temporalio.exceptions import ApplicationError

from program.temporal.orchestration import shared
from utils.logger import logger


@workflow.defn(name=shared.RETRIES_WORKFLOW, sandboxed=False)
class RetriesWorkflow:
    @workflow.run
    async def run(self, params=None):
        from program.temporal.retries.retries_activities import obtain_and_retry_partial_mediaitems
        try:
            await workflow.execute_activity(
                obtain_and_retry_partial_mediaitems,
                start_to_close_timeout=timedelta(minutes=1),
                retry_policy=RetryPolicy(maximum_attempts=1))
            return {"status": "success"}
        except Exception as e:
            raise ApplicationError(f"Error running RetriesWorkflow: {e}")