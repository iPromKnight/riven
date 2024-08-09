from dependency_injector import containers, providers
from temporalio.client import Client
import program.temporal.literals as literals 
from program.content import Listrr, Mdblist, Overseerr, PlexWatchlist
from program.downloaders import Downloader
from program.indexers.trakt import TraktIndexer
from program.libraries import SymlinkLibrary
from program.scrapers import Scraping
from program.symlink import Symlinker
from program.updaters import Updater
from utils.logger import logger


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
    temporal_client = providers.Resource(
        Client.connect,
        target_host=f"{literals.TEMPORAL_HOST}:{literals.TEMPORAL_PORT}",
        namespace=literals.TEMPORAL_NAMESPACE)

    def check_dependencies(self) -> bool:
        return self.verify_initialization()

    def verify_initialization(self):
        requesting_services = {
            "Overseerr": self.overseerr(),
            "PlexWatchlist": self.plex_watchlist(),
            "Listrr": self.listrr(),
            "Mdblist": self.mdblist(),
        }

        processing_services = {
            "Scraping": self.scraping(),
            "Symlinker": self.symlinker(),
            "Updater": self.updater(),
            "Downloader": self.downloader(),
        }

        library_services = {
            "SymlinkLibrary": self.symlink_library(),
        }

        if not any(s.initialized for s in requesting_services.values()):
            logger.error("No Requesting service initialized, you must enable at least one.")
            return False
        if not processing_services["Scraping"].initialized:
            logger.error("No Scraping service initialized, you must enable at least one.")
            return False
        if not processing_services["Downloader"].initialized:
            logger.error("No Downloader service initialized, you must enable at least one.")
            return False
        if not processing_services["Updater"].initialized:
            logger.error("No Updater service initialized, you must enable at least one.")
            return False
        if not library_services["SymlinkLibrary"].initialized:
            logger.error("No SymlinkLibrary service initialized, you must enable at least one.")
            return False
        return True