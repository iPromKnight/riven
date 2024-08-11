from pathlib import Path
from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from program.db.db import db


class Subtitle(db.Model):
    __tablename__ = "Subtitle"
    
    _id: Mapped[int] = mapped_column(Integer, primary_key=True)
    language: Mapped[str] = mapped_column(String)
    file: Mapped[str] = mapped_column(String, nullable=True)
    
    parent_id: Mapped[int] = mapped_column(Integer, ForeignKey("MediaItem._id", ondelete="CASCADE"))
    parent: Mapped["MediaItem"] = relationship("MediaItem", back_populates="subtitles")
   
    def __init__(self, optional={}):
        for key in optional.keys():
            self.language = key
            self.file = optional[key]
    
    def remove(self):
        if self.file and Path(self.file).exists():
            Path(self.file).unlink()
        self.file = None
        return self