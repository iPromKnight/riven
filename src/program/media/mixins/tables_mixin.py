from sqlalchemy.orm import declared_attr


class TablesMixinSchema:
    @declared_attr
    def __tablename__(self):
        return self.__name__