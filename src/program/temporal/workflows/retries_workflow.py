from datetime import timedelta
import program.temporal.literals as literals
from temporalio import workflow
from program.temporal.activities import RetriesActivity


@workflow.defn(name=literals.RETRIES_WORKFLOW, sandboxed=False)
class RetriesWorkflow:
    @workflow.run
    async def run(self, params=None):
        await workflow.execute_activity(RetriesActivity(), args=[],  start_to_close_timeout=timedelta(minutes=1))