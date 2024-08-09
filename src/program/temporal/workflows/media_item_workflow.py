from temporalio import workflow
import program.temporal.literals as literals
from program.temporal.activities import ScrapedActivity, IndexedActivity, RequestedActivity, DownloadedActivity, SymlinkedActivity
from program.media import MediaItem, States


@workflow.defn(name=literals.MEDIA_ITEM_WORKFLOW, sandboxed=False)
class MediaItemWorkflow:
    @workflow.run
    async def run(self, item: MediaItem):
        next_service = None
        while item.state != States.Completed:
            if item.state == States.Requested:
                item, next_service = await workflow.execute_activity(RequestedActivity(), args=[item])
            elif item.state == States.Indexed:
                item, next_service = await workflow.execute_activity(IndexedActivity(), args=[item])
            elif item.state == States.Scraped:
                item, next_service = await workflow.execute_activity(ScrapedActivity(), args=[item])
            elif item.state == States.Downloaded:
                item, next_service = await workflow.execute_activity(DownloadedActivity(), args=[item])
            elif item.state == States.Symlinked:
                item, next_service = await workflow.execute_activity(SymlinkedActivity(), args=[item])

            if next_service is None:
                break

            item.state = self.get_next_state(next_service)

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