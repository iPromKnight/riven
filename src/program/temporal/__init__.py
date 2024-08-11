from program.temporal.retries import retries_activities, RetriesWorkflow
from program.temporal.mediaitems import media_item_activities, MediaItemWorkflow
from program.temporal.overseer import overseerr_activities, OverseerrWorkflow
from program.temporal.orchestration import schedules, workflows


def activities() -> []:
    return media_item_activities() + overseerr_activities() + retries_activities()


def workflows() -> []:
    return [MediaItemWorkflow, OverseerrWorkflow, RetriesWorkflow]