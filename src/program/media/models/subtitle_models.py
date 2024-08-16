from pathlib import Path

from program.media.riven_base import RivenBaseModel


class SubtitleModel(RivenBaseModel):
    language: str
    file: str
    parent_id: int
    parent: "MediaItemSchema"
   
    def __init__(self, optional={}):
        for key in optional.keys():
            self.language = key
            self.file = optional[key]
    
    def remove(self):
        if self.file and Path(self.file).exists():
            Path(self.file).unlink()
        self.file = None
        return self