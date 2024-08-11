import temporalio.activity
from kink import di

from program.downloaders import Downloader
from program.indexers import TraktIndexer
from program.media import MediaItem, Episode, Movie, Season, Show
from program.post_processing import PostProcessing
from program.scrapers import Scraping
from program.symlink import Symlinker
from program.updaters import Updater
from utils.logger import logger


@temporalio.activity.defn
async def handle_requested_or_unknown_state(item: MediaItem) -> MediaItem:
    trakt_indexer = di[TraktIndexer]
    if trakt_indexer.should_submit(item):
        item = trakt_indexer.run(item)
    return item


@temporalio.activity.defn
async def handle_indexed_or_partially_completed_state(item: MediaItem) -> MediaItem:
    scraping = di[Scraping]
    if scraping.should_submit(item):
        item = scraping.run(item)
    return item


@temporalio.activity.defn
async def handle_scraped_state(item: MediaItem) -> MediaItem:
    downloader = di[Downloader]
    downloader.run(item)
    return item


@temporalio.activity.defn
async def handle_downloaded_state(item: MediaItem) -> MediaItem:
    symlinker = di[Symlinker]
    proposed_submissions = []
    # media_type = item["type"]
    # if media_type == "show":
    #     model = ShowData.model_validate(item)
    #     all_found = all(
    #         all(e.file and e.folder for e in season.episodes if not e.symlinked)
    #         for season in model.seasons
    #     )
    #     if all_found:
    #         proposed_submissions = [model]
    #     else:
    #         proposed_submissions = [
    #             e for season in model.seasons
    #             for e in model.episodes
    #             if not e.symlinked and e.file and e.folder
    #         ]
    #     return model
    # elif media_type == "season":
    #     model = SeasonData.model_validate(item)
    #     if all(e.file and e.folder for e in model.episodes if not e.symlinked):
    #         proposed_submissions = [model]
    #     else:
    #         proposed_submissions = [e for e in model.episodes if not e.symlinked and e.file and e.folder]
    #     return model
    # elif media_type == "movie":
    #     model = MovieData.model_validate(item)
    #     proposed_submissions = [model]
    #     return model
    # elif media_type == "episode":
    #     model = EpisodeData.model_validate(item)
    #     proposed_submissions = [model]
    return item


@temporalio.activity.defn
async def handle_symlinked_state(item: MediaItem) -> MediaItem:
    updater = di[Updater]
    updater.run(item)
    return item


@temporalio.activity.defn
async def handle_completed_state(item: MediaItem) -> MediaItem:
    post_processor = di[PostProcessing]
    item = post_processor.run(item)
    return item


@temporalio.activity.defn
async def store_item(item: MediaItem):
    try:
        from program.db import PostgresRepository
        PostgresRepository.update_item_in_db(item)
        logger.log("DATABASE", f"Item {item.item_id} stored in database.")
    except Exception as e:
        logger.error(f"Error storing item {item.item_id} with state {item.state.value}: {e}")
        raise e