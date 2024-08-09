import temporalio.activity
from dependency_injector.wiring import inject, Provide

from program.downloaders import Downloader
from program.indexers import TraktIndexer
from program.media import MediaItem, States, EpisodeData, MovieData, SeasonData, ShowData, MediaItemData
from program.scrapers import Scraping
from program.symlink import Symlinker
from program.temporal.service_container import ServiceContainer
from program.updaters import Updater


@temporalio.activity.defn
class HandleRequestedOrUnknown:
    @inject
    async def __call__(self, existing_item: MediaItemData | None, item: MediaItemData,
                       trakt_indexer: TraktIndexer = Provide[ServiceContainer.trakt_indexer]) -> MediaItemData:
        if isinstance(item, SeasonData):
            item = item.parent
            existing_item = existing_item.parent if existing_item else None
        if existing_item and not trakt_indexer.should_submit(existing_item):
            return item
        return item


@temporalio.activity.defn
class HandleIndexedOrPartiallyCompleted:
    @inject
    async def __call__(self, existing_item: MediaItem | None, item: MediaItem,
                       scraping: Scraping = Provide[ServiceContainer.scraping]) -> MediaItemData:
        if existing_item:
            if not existing_item.indexed_at:
                if isinstance(item, (ShowData, SeasonData)):
                    existing_item.fill_in_missing_children(item)
                existing_item.copy_other_media_attr(item)
                existing_item.indexed_at = item.indexed_at
                item = existing_item
            if existing_item.state == States.Completed:
                return existing_item
        return item


@temporalio.activity.defn
class HandleScraped:
    @inject
    async def __call__(self, item: MediaItemData,
                       downloader: Downloader = Provide[ServiceContainer.downloader]) -> MediaItemData:
        return item


@temporalio.activity.defn
class HandleDownloaded:
    @inject
    async def __call__(self, item: MediaItemData,
                       symlinker: Symlinker = Provide[ServiceContainer.symlinker]) -> MediaItemData:
        proposed_submissions = []
        media_type = item["type"]
        if media_type == "show":
            model = ShowData.model_validate(item)
            all_found = all(
                all(e.file and e.folder for e in season.episodes if not e.symlinked)
                for season in model.seasons
            )
            if all_found:
                proposed_submissions = [model]
            else:
                proposed_submissions = [
                    e for season in model.seasons
                    for e in model.episodes
                    if not e.symlinked and e.file and e.folder
                ]
            return model
        elif media_type == "season":
            model = SeasonData.model_validate(item)
            if all(e.file and e.folder for e in model.episodes if not e.symlinked):
                proposed_submissions = [model]
            else:
                proposed_submissions = [e for e in model.episodes if not e.symlinked and e.file and e.folder]
            return model
        elif media_type == "movie":
            model = MovieData.model_validate(item)
            proposed_submissions = [model]
            return model
        elif media_type == "episode":
            model = EpisodeData.model_validate(item)
            proposed_submissions = [model]
            return model


@temporalio.activity.defn
class HandleSymlinked:
    @inject
    async def __call__(self, item: MediaItemData, updater: Updater = Provide[ServiceContainer.updater]) -> MediaItemData:
        return item


@temporalio.activity.defn
class HandleCompleted:
    async def __call__(self, item: MediaItemData) -> MediaItemData:
        return item