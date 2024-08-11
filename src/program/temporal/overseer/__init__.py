from .overseerr_activities import scan_overseerr_requests  # noqa
from .overseerr_workflow import OverseerrWorkflow  # noqa


def overseerr_activities() -> []:
    return [
        scan_overseerr_requests
    ]