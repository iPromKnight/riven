import temporalio.activity
from dependency_injector.wiring import inject, Provide
from sqlalchemy import select, func
from temporalio.client import Client
import program.temporal.literals as literals
from program.temporal.service_container import ServiceContainer
from utils.logger import logger
from program import MediaItem
from program.db.db import db


@temporalio.activity.defn
class RetriesActivity:
    @inject
    async def __call__(
            self,
            client: Client = Provide[ServiceContainer.temporal_client]):
        with db.Session() as session:
            count = session.execute(
                select(func.count(MediaItem._id))
                .where(MediaItem.type.in_(["movie", "show"]))
                .where(MediaItem.last_state != "Completed")
            ).scalar_one()
        logger.log("PROGRAM", f"Found {count} items to retry")

        number_of_rows_per_page = 10
        for page_number in range(0, (count // number_of_rows_per_page) + 1):
            with db.Session() as session:
                items_to_submit = session.execute(
                    select(MediaItem)
                    .where(MediaItem.type.in_(["movie", "show"]))
                    .where(MediaItem.last_state != "Completed")
                    .order_by(MediaItem.requested_at.desc())
                    .limit(number_of_rows_per_page)
                    .offset(page_number * number_of_rows_per_page)
                ).unique().scalars().all()
                for item in items_to_submit:
                    workflow_id = item.item_id
                    try:
                        await client.start_workflow(
                            workflow=literals.MEDIA_ITEM_WORKFLOW,
                            arg=item,
                            task_queue=literals.TASK_QUEUE,
                            id=workflow_id)
                        logger.log("PROGRAM", f"Starting Retry run with {literals.MEDIA_ITEM_WORKFLOW} workflow for item id: {workflow_id}")
                    except Exception as e:
                        if "Workflow execution already started" in str(e):
                            return
                        logger.error(f"Error starting workflow {workflow_id}: {e}")