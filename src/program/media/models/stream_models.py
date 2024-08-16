from RTN import Torrent

from program.media.riven_base import RivenBaseModel


class StreamRelationModel(RivenBaseModel):
    parent_id: int
    child_id: int


class StreamBlacklistRelationModel(RivenBaseModel):
    media_item_id: int
    stream_id: int


class StreamModel(RivenBaseModel):
    infohash: str
    raw_title: str
    parsed_title: str
    rank: int
    lev_ratio: float
    parents: list["MediaItemSchema"]
    blacklisted_parents: list["MediaItemSchema"]

    def __init__(self, torrent: Torrent):
        self.raw_title = torrent.raw_title
        self.infohash = torrent.infohash
        self.parsed_title = torrent.data.parsed_title
        self.rank = torrent.rank
        self.lev_ratio = torrent.lev_ratio

    def __hash__(self):
        return self.infohash

    def __eq__(self, other):
        return isinstance(other, StreamModel) and self.infohash == other.infohash