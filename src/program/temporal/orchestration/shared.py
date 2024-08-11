from datetime import timedelta

from temporalio.common import RetryPolicy

TEMPORAL_HOST = "localhost"
TEMPORAL_PORT = 7233
TEMPORAL_NAMESPACE = "riven"

RETRIES_WORKFLOW = "Retries"
MEDIA_ITEM_WORKFLOW = "MediaItem"
OVERSEERR_WORKFLOW = "Overseerr"

RETRIES_SCHEDULE = "riven-retries-schedule-workflow"
OVERSEERR_SCHEDULE = "riven-overseerr-schedule-workflow"

TASK_QUEUE = "riven-task-queue"
NUMBER_OF_ROWS_PER_PAGE = 10

MEDIA_ITEM_RETRY_ATTEMPTS = 1
MEDIA_ITEM_RETRY_POLICY = RetryPolicy(maximum_attempts=1)
MEDIA_ITEM_EXECUTION_TIMEOUT = timedelta(minutes=10)