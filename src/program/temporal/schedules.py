import program.temporal.literals as literals
from datetime import timedelta
from program.temporal.workflows import RetriesWorkflow
from temporalio.client import (
    Client,
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleSpec,
    ScheduleIntervalSpec,
)


async def create_retries_schedule(client: Client):
    await client.create_schedule(
        literals.RETRIES_SCHEDULE,
        Schedule(
            action=ScheduleActionStartWorkflow(
                RetriesWorkflow.run,
                id=literals.RETRIES_SCHEDULE,
                task_queue=literals.TASK_QUEUE,
            ),
            spec=ScheduleSpec(
                intervals=[ScheduleIntervalSpec(every=timedelta(seconds=10))],
            )
        ))


class RivenWorkflowSchedules():
    def __init__(self, client: Client):
        self.client = client

    async def create_schedules(self):
        await create_retries_schedule(self.client)