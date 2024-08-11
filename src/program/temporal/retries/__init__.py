from .retries_activities import obtain_and_retry_partial_mediaitems  # noqa
from .retries_workflow import RetriesWorkflow  # noqa


def retries_activities() -> []:
    return [obtain_and_retry_partial_mediaitems]