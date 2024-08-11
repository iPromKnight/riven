from datetime import timedelta
from temporalio.common import RetryPolicy
from temporalio import workflow
from temporalio.exceptions import ApplicationError

from program.temporal.orchestration import shared
from utils.logger import logger


@workflow.defn(name=shared.OVERSEERR_WORKFLOW, sandboxed=False)
class OverseerrWorkflow:
    @workflow.run
    async def run(self, params=None):
        from program.temporal.overseer import scan_overseerr_requests
        try:
            logger.info("Running OverseerrWorkflow")
            await workflow.execute_activity(
                scan_overseerr_requests,
                start_to_close_timeout=timedelta(minutes=3),
                retry_policy=RetryPolicy(maximum_attempts=1))
            return {"status": "success"}
        except Exception as e:
            raise ApplicationError(f"Error running OverseerrWorkflow: {e}")