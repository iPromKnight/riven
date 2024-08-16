from program.db.repositories.repository_base import BaseRepository
from program.media import MediaItemModel, MediaItem


class MediaItemRepository(BaseRepository[MediaItemModel, MediaItem]):
    def __init__(self):
        super().__init__(MediaItem)