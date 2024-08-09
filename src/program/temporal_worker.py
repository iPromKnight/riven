from google.protobuf.duration_pb2 import Duration
from temporalio.api.workflowservice.v1 import RegisterNamespaceRequest, UpdateNamespaceRequest, DescribeNamespaceRequest
from temporalio.client import Client
from program.service_container import ServiceContainer
from temporalio.worker import Worker
from program.settings.manager import settings_manager
from program.settings.models import TemporalModel
from program.workflows.media_item_workflow import MediaItemWorkflow
from program.activities import (
    ScrapedActivity,
    IndexedActivity,
    RequestedActivity,
    DownloadedActivity,
    SymlinkedActivity
)
from utils.logger import logger

TASK_QUEUE = "riven-task-queue"


async def create_namespace(temporal_settings: TemporalModel, retention_period: int):
    client = await Client.connect(temporal_settings.url)
    riven_namespace = RegisterNamespaceRequest(
        namespace=temporal_settings.namespace,
        workflow_execution_retention_period={"seconds": retention_period},
        description=f"Riven Temporal namespace: {temporal_settings.namespace}",
    )
    await client.workflow_service.register_namespace(riven_namespace)
    logger.debug(f"Namespace '{temporal_settings.namespace}' created successfully.")


async def update_namespace(temporal_settings: TemporalModel, retention_period: int):
    try:
        client = await Client.connect(temporal_settings.url)
        describe_request = DescribeNamespaceRequest(namespace=temporal_settings.namespace)
        current_namespace_info = await client.workflow_service.describe_namespace(describe_request)
        if not current_namespace_info.config:
            logger.error("Failed to retrieve current namespace config.")
            exit(1)
        current_namespace_info.config.workflow_execution_retention_ttl.seconds = retention_period
        update_request = UpdateNamespaceRequest(
            namespace=temporal_settings.namespace,
            config=current_namespace_info.config
        )
        await client.workflow_service.update_namespace(update_request)
        logger.debug(f"Namespace '{temporal_settings.namespace}' updated successfully.")
        return
    except Exception as e:
        logger.error(f"Error updating namespace '{temporal_settings.namespace}': {e}")
        exit(1)


async def ensure_namespace_exists(temporal_settings: TemporalModel):
    retention_period = (temporal_settings.workflow_retention_period_days * 86400)
    try:
        await create_namespace(temporal_settings, retention_period)
    except Exception as e:
        if "Namespace already exists" in str(e):
            await update_namespace(temporal_settings, retention_period)
            return
        logger.error(f"Error creating namespace '{temporal_settings.namespace}': {e}")
        exit(1)


class RivenTemporalWorker:
    def __init__(self):
        self.worker = None

    async def create_worker(self):
        temporal_settings = settings_manager.settings.temporal
        container = ServiceContainer()
        container.wire(modules=[__name__])

        await ensure_namespace_exists(temporal_settings)

        client = await Client.connect(temporal_settings.url, namespace=temporal_settings.namespace)

        self.worker = Worker(
            client,
            task_queue=TASK_QUEUE,
            workflows=[MediaItemWorkflow],
            activities=[
                RequestedActivity(),
                IndexedActivity(),
                ScrapedActivity(),
                DownloadedActivity(),
                SymlinkedActivity(),
            ],
        )

        logger.info("Worker created successfully.")

    async def start(self):
        if not self.worker:
            await self.create_worker()
        await self.worker.run()

    async def stop(self):
        if self.worker:
            self.worker.shutdown()