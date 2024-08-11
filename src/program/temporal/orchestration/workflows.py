from kink import inject
from temporalio.client import Client
from temporalio.common import WorkflowIDReusePolicy

from program.media import MediaItem
from utils.logger import logger
from program.temporal.orchestration import shared


@inject
async def start_media_item_workflow(item: MediaItem, temporal_client: Client):
    workflow_id = item.item_id or item._id
    try:
        await temporal_client.start_workflow(
            workflow=shared.MEDIA_ITEM_WORKFLOW,
            arg=item,
            task_queue=shared.TASK_QUEUE,
            retry_policy=shared.MEDIA_ITEM_RETRY_POLICY,
            execution_timeout=shared.MEDIA_ITEM_EXECUTION_TIMEOUT,
            id_reuse_policy=WorkflowIDReusePolicy.TERMINATE_IF_RUNNING,
            id=workflow_id)
        logger.info(f"Running {shared.MEDIA_ITEM_WORKFLOW} workflow for item id: {workflow_id}")
    except Exception as e:
        if "Workflow execution already started" in str(e):
            return
        logger.error(f"Error starting workflow {workflow_id}: {e}")


@inject
async def stop_media_item_workflow(workflow_id: str, temporal_client: Client) -> bool:
    try:
        workflow_exists = await temporal_client.workflow_service.describe_workflow_execution(
            workflow_id=workflow_id,
            namespace=shared.TEMPORAL_NAMESPACE,
            task_queue=shared.TASK_QUEUE)
        if not workflow_exists:
            logger.debug(f"Workflow {workflow_id} does not exist. Skipping Termination");
            return True
        if workflow_exists.workflow_execution_info.status == "COMPLETED":
            logger.debug(f"Workflow {workflow_id} already completed. Skipping Termination");
            return True
        result = await temporal_client.workflow_service.terminate_workflow_execution(
            workflow_id=workflow_id,
            namespace=shared.TEMPORAL_NAMESPACE,
            task_queue=shared.TASK_QUEUE)
        if result:
            logger.info(f"Terminated {shared.MEDIA_ITEM_WORKFLOW} workflow for item id: {workflow_id}")
            return True
    except Exception as e:
        logger.error(f"Error terminating workflow {workflow_id}: {e}")
        return False