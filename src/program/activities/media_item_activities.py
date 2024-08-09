import temporalio.activity
from dependency_injector.wiring import inject, Provide
from program.downloaders import Downloader
from program.indexers import TraktIndexer
from program.media import Season
from program.scrapers import Scraping
from program.service_container import ServiceContainer
from program.symlink import Symlinker
from program.updaters import Updater


@temporalio.activity.defn
class RequestedActivity:
    @inject
    async def __call__(
            self,
            item,
            trakt_indexer: TraktIndexer = Provide[ServiceContainer.trakt_indexer]
    ):
        if isinstance(item, Season):
            item = item.parent
        if trakt_indexer.should_submit(item):
            return item, trakt_indexer
        return item, None


@temporalio.activity.defn
class IndexedActivity:
    @inject
    async def __call__(
            self,
            item,
            scraping: Scraping = Provide[ServiceContainer.scraping]
    ):
        if scraping.can_we_scrape(item):
            return item, scraping
        return item, None


@temporalio.activity.defn
class ScrapedActivity:
    @inject
    async def __call__(
            self,
            item,
            downloader: Downloader = Provide[ServiceContainer.downloader]
    ):
        return item, downloader


@temporalio.activity.defn
class DownloadedActivity:
    @inject
    async def __call__(
            self,
            item,
            symlinker: Symlinker = Provide[ServiceContainer.symlinker]
    ):
        if symlinker.should_submit(item):
            return item, symlinker
        return item, None


@temporalio.activity.defn
class SymlinkedActivity:
    @inject
    async def __call__(
            self,
            item,
            updater: Updater = Provide[ServiceContainer.updater]
    ):
        return item, updater