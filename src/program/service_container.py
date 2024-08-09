from dependency_injector import containers, providers
from program.content import Listrr, Mdblist, Overseerr, PlexWatchlist
from program.downloaders import Downloader
from program.indexers.trakt import TraktIndexer
from program.libraries import SymlinkLibrary
from program.scrapers import Scraping
from program.symlink import Symlinker
from program.updaters import Updater


class ServiceContainer(containers.DeclarativeContainer):
    overseerr = providers.Singleton(Overseerr)
    plex_watchlist = providers.Singleton(PlexWatchlist)
    listrr = providers.Singleton(Listrr)
    mdblist = providers.Singleton(Mdblist)
    trakt_indexer = providers.Singleton(TraktIndexer)
    downloader = providers.Singleton(Downloader)
    symlink_library = providers.Singleton(SymlinkLibrary)
    scraping = providers.Singleton(Scraping)
    symlinker = providers.Singleton(Symlinker)
    updater = providers.Singleton(Updater)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)