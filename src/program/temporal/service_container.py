from kink import di
from temporalio.client import Client
from program.content import Listrr, Mdblist, Overseerr, PlexWatchlist
from program.downloaders import Downloader
from program.indexers.trakt import TraktIndexer
from program.libraries import SymlinkLibrary
from program.post_processing import PostProcessing
from program.scrapers import Scraping
from program.settings.manager import SettingsManager
from program.symlink import Symlinker
from program.temporal.orchestration import shared
from program.updaters import Updater


class ServiceContainer:
    async def bootstrap(self):
        di["Overseerr"] = Overseerr()
        di["PlexWatchlist"] = PlexWatchlist()
        di["Listrr"] = Listrr()
        di["Mdblist"] = Mdblist()
        di["TraktIndexer"] = TraktIndexer()
        di["Downloader"] = Downloader()
        di["SymlinkLibrary"] = SymlinkLibrary()
        di["Scraping"] = Scraping()
        di["Symlinker"] = Symlinker()
        di["Updater"] = Updater()
        di["SettingsManager"] = SettingsManager()
        di["PostProcessing"] = PostProcessing()
        await self.__create_temporal_client()
        self.__create_service_collections()
        self.__validate_services()

    @staticmethod
    async def __create_temporal_client():
        temporal_client = await Client.connect(
            target_host=f"{shared.TEMPORAL_HOST}:{shared.TEMPORAL_PORT}",
            namespace=shared.TEMPORAL_NAMESPACE)
        di["temporal_client"] = temporal_client

    @staticmethod
    def __create_service_collections():
        di["requesting_services"] = {
            "Overseerr": di["Overseerr"],
            "PlexWatchlist": di["PlexWatchlist"],
            "Listrr": di["Listrr"],
            "Mdblist": di["Mdblist"],
        }

        di["processing_services"] = {
            "Scraping": di["Scraping"],
            "Symlinker": di["Symlinker"],
            "Updater": di["Updater"],
            "Downloader": di["Downloader"],
        }

        di["library_services"] = {
            "SymlinkLibrary": di["SymlinkLibrary"],
        }

        di["postprocessing_services"] = {
            "PostProcessing": di["PostProcessing"],
        }

    @staticmethod
    def __validate_services():
        if not any(s.initialized for s in di["requesting_services"].values()):
            raise ValueError("No Requesting service initialized, you must enable at least one.")
        if not di["processing_services"]["Scraping"].initialized:
            raise ValueError("No Scraping service initialized, you must enable at least one.")
        if not di["processing_services"]["Downloader"].initialized:
            raise ValueError("No Downloader service initialized, you must enable at least one.")
        if not di["processing_services"]["Updater"].initialized:
            raise ValueError("No Updater service initialized, you must enable at least one.")
        if not di["library_services"]["SymlinkLibrary"].initialized:
            raise ValueError("No SymlinkLibrary service initialized, you must enable at least one.")
        if not di["temporal_client"]:
            raise ValueError("No Temporal client initialized, Please check configuration, or inspect the temporal service.")