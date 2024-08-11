from kink import inject

import program.temporal.orchestration.shared as shared
from datetime import timedelta

from program.content import Overseerr
from program.settings.manager import SettingsManager
from program.settings.models import AppModel
from program.temporal.overseer.overseerr_workflow import OverseerrWorkflow
from program.temporal.retries.retries_workflow import RetriesWorkflow
from temporalio.client import (
    Client,
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleSpec,
    ScheduleIntervalSpec,
)

from utils.logger import logger

RETRIES_SCHEDULE = ScheduleIntervalSpec(every=timedelta(minutes=10))


async def _create_retries_schedule(client: Client):
    await client.create_schedule(
        shared.RETRIES_SCHEDULE,
        Schedule(
            action=ScheduleActionStartWorkflow(
                RetriesWorkflow.run,
                id=shared.RETRIES_SCHEDULE,
                task_queue=shared.TASK_QUEUE,
            ),
            spec=ScheduleSpec(
                intervals=[RETRIES_SCHEDULE],
            )
        ))


async def _create_overseerr_schedule(client: Client, settings: AppModel):
    schedule_interval = settings.content.overseerr.update_interval
    await client.create_schedule(
        shared.OVERSEERR_SCHEDULE,
        Schedule(
            action=ScheduleActionStartWorkflow(
                OverseerrWorkflow.run,
                id=shared.OVERSEERR_SCHEDULE,
                task_queue=shared.TASK_QUEUE,
            ),
            spec=ScheduleSpec(
                intervals=[ScheduleIntervalSpec(every=timedelta(seconds=schedule_interval))],
            )
        ))


async def _delete_overseerr_schedule(client: Client):
    try:
        schedule = client.get_schedule_handle(shared.OVERSEERR_SCHEDULE)
        if not schedule:
            return
        await schedule.delete()
    except Exception as e:
        if not "no rows in result set" in str(e):
            logger.error(f"Error deleting Overseerr schedule: {str(e)}")


@inject
async def create_schedules(
        temporal_client: Client,
        settings_manager: SettingsManager,
        overseerr: Overseerr):
    if settings_manager.settings.content.overseerr.enabled and overseerr.initialized:
        await _create_overseerr_schedule(temporal_client, settings_manager.settings)
    else:
        await _delete_overseerr_schedule(temporal_client)

    await _create_retries_schedule(temporal_client)