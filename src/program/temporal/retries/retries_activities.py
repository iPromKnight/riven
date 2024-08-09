import temporalio.activity
from program.db import db_functions
from dependency_injector.wiring import inject, Provide
from temporalio.client import Client
import program.temporal.literals as literals
from program.temporal.service_container import ServiceContainer
from utils.logger import logger

NUMBER_OF_ROWS_PER_PAGE = 10


@temporalio.activity.defn
class RetriesActivity:
    @inject
    async def __call__(
            self,
            client: Client = Provide[ServiceContainer.temporal_client]):
        item_count = db_functions.get_items_to_retry_count()
        if item_count == 0:
            logger.debug("No items to retry")
            return
        for page_number in range(0, (item_count // NUMBER_OF_ROWS_PER_PAGE) + 1):
            items_to_submit = db_functions.get_items_to_retry_for_page(NUMBER_OF_ROWS_PER_PAGE, page_number)
            for item in items_to_submit:
                workflow_id = item.item_id
                try:
                    item_to_process = item.to_pydantic()
                    await client.start_workflow(
                        workflow=literals.MEDIA_ITEM_WORKFLOW,
                        arg=item_to_process.model_dump(),
                        task_queue=literals.TASK_QUEUE,
                        id=workflow_id)
                    logger.log("PROGRAM", f"Running {literals.MEDIA_ITEM_WORKFLOW} workflow for item id: {workflow_id}")
                except Exception as e:
                    if "Workflow execution already started" in str(e):
                        return
                    logger.error(f"Error starting workflow {workflow_id}: {e}")