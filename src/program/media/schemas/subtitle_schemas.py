from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from program.media.riven_base import RivenBaseSchema


class Subtitle(RivenBaseSchema):
    language: Mapped[str] = mapped_column(String)
    file: Mapped[str] = mapped_column(String, nullable=True)

    parent_id: Mapped[int] = mapped_column(Integer, ForeignKey("MediaItem.id", ondelete="CASCADE"))
    parent: Mapped["MediaItem"] = relationship("MediaItem", back_populates="subtitles")