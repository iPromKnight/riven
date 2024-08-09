from datetime import timedelta
import program.temporal.literals as literals
from temporalio import workflow
from program.temporal.retries import RetriesActivity


@workflow.defn(name=literals.RETRIES_WORKFLOW, sandboxed=False)
class RetriesWorkflow:
    @workflow.run
    async def run(self, params=None):
        try:
            await workflow.execute_activity(RetriesActivity(), start_to_close_timeout=timedelta(minutes=1))
            return {"status": "success"}
        except Exception as e:
            return {"status": "failure", "message": str(e)}