from datetime import timedelta

from temporalio import workflow
import program.temporal.literals as literals
from program.media.data_models import MediaItemData
from program.temporal.mediaitems import HandleRequestedOrUnknown, HandleIndexedOrPartiallyCompleted, HandleScraped, HandleDownloaded, HandleSymlinked, HandleCompleted # noqa
from program.media import States


@workflow.defn(name=literals.MEDIA_ITEM_WORKFLOW, sandboxed=False)
class MediaItemWorkflow:
    @workflow.run
    async def run(self, item: MediaItemData):
        try:
            next_service = None
            while item.state != States.Completed:
                if item.state == States.Requested.value:
                    item, next_service = await workflow.execute_activity(HandleRequestedOrUnknown(), args=[item], start_to_close_timeout=timedelta(minutes=1))
                elif item.state == States.Indexed.value:
                    item, next_service = await workflow.execute_activity(HandleIndexedOrPartiallyCompleted(), args=[item], start_to_close_timeout=timedelta(minutes=1))
                elif item.state == States.Scraped.value:
                    item, next_service = await workflow.execute_activity(HandleScraped(), args=[item], start_to_close_timeout=timedelta(minutes=1))
                elif item.state == States.Downloaded.value:
                    item, next_service = await workflow.execute_activity(HandleDownloaded(), args=[item], start_to_close_timeout=timedelta(minutes=2))
                elif item.state == States.Symlinked.value:
                    item, next_service = await workflow.execute_activity(HandleSymlinked(), arg=item, start_to_close_timeout=timedelta(minutes=2))

                if next_service is None:
                    break

                item.state = self.get_next_state(next_service)

            return {"status": "success", "state": item.state.value}
        except Exception as e:
            return {"status": "failure", "message": str(e)}

    @staticmethod
    def get_next_state(next_service) -> States | None:
        service_to_state = {
            'TraktIndexer': States.Indexed,
            'Scraping': States.Scraped,
            'Downloader': States.Downloaded,
            'Symlinker': States.Symlinked,
            'Updater': States.Completed,
        }
        return service_to_state.get(next_service.__class__.__name__)