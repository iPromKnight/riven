import json

from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.orm import declared_attr


class AlchemyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj.__class__, DeclarativeMeta):
            fields = {}
            for field in [x for x in dir(obj) if not x.startswith('_') and x != 'metadata']:
                data = obj.__getattribute__(field)
                try:
                    json.dumps(data)
                    fields[field] = data
                except TypeError:
                    fields[field] = None
            return fields

        return json.JSONEncoder.default(self, obj)


class RivenBaseMixin:
    @declared_attr
    def __tablename__(self):
        return self.__name__

    def to_temporal_dict(self):
        json_item = json.dumps(self, cls=AlchemyEncoder)
        return json.loads(json_item)