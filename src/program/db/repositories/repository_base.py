from typing import Type, TypeVar, Generic, List, Union
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from program.media.riven_base import RivenBaseModel, RivenBaseSchema

TModel = TypeVar('TModel', bound=RivenBaseModel)
TSchema = TypeVar('TSchema', bound=RivenBaseSchema)


class RepositoryException(Exception):
    pass


class IntegrityConflictException(Exception):
    pass


class NotFoundException(Exception):
    pass


class BaseRepository(Generic[TModel, TSchema]):
    def __init__(self, model: Type[TSchema]):
        self.model = model

    async def create(
            self,
            session: AsyncSession,
            data: TModel,
    ) -> TSchema:
        try:
            db_model = self.model(**data.model_dump())
            session.add(db_model)
            await session.commit()
            await session.refresh(db_model)
            return db_model
        except IntegrityError:
            raise IntegrityConflictException(
                f"{self.model.__tablename__} conflicts with existing data.",
            )
        except Exception as e:
            raise RepositoryException(f"Unknown error occurred: {e}") from e

    async def create_many(
            self,
            session: AsyncSession,
            data: List[TModel],
            return_models: bool = False,
    ) -> Union[List[TSchema], bool]:
        db_models = [self.model(**d.model_dump()) for d in data]
        try:
            session.add_all(db_models)
            await session.commit()
        except IntegrityError:
            raise IntegrityConflictException(
                f"{self.model.__tablename__} conflicts with existing data.",
            )
        except Exception as e:
            raise RepositoryException(f"Unknown error occurred: {e}") from e

        if not return_models:
            return True

        for m in db_models:
            await session.refresh(m)

        return db_models

    async def get_one_by_id(
            self,
            session: AsyncSession,
            id_: Union[str, int],
            column: str = "id",
            with_for_update: bool = False,
    ) -> TSchema:
        try:
            q = select(self.model).where(getattr(self.model, column) == id_)
        except AttributeError:
            raise RepositoryException(
                f"Column {column} not found on {self.model.__tablename__}.",
            )

        if with_for_update:
            q = q.with_for_update()

        results = await session.execute(q)
        return results.unique().scalar_one_or_none()

    async def get_many_by_ids(
            self,
            session: AsyncSession,
            ids: List[Union[str, int]] = None,
            column: str = "id",
            with_for_update: bool = False,
    ) -> List[TSchema]:
        q = select(self.model)
        if ids:
            try:
                q = q.where(getattr(self.model, column).in_(ids))
            except AttributeError:
                raise RepositoryException(
                    f"Column {column} not found on {self.model.__tablename__}.",
                )

        if with_for_update:
            q = q.with_for_update()

        rows = await session.execute(q)
        return rows.unique().scalars().all()

    async def update_by_id(
            self,
            session: AsyncSession,
            data: TModel,
            id_: Union[str, int],
            column: str = "id",
    ) -> TSchema:
        db_model = await self.get_one_by_id(
            session, id_, column=column, with_for_update=True
        )
        if not db_model:
            raise NotFoundException(
                f"{self.model.__tablename__} {column}={id_} not found.",
            )

        values = data.model_dump(exclude_unset=True)
        for k, v in values.items():
            setattr(db_model, k, v)

        try:
            await session.commit()
            await session.refresh(db_model)
            return db_model
        except IntegrityError:
            raise IntegrityConflictException(
                f"{self.model.__tablename__} {column}={id_} conflicts with existing data.",
            )

    async def update_many_by_ids(
            self,
            session: AsyncSession,
            updates: dict[Union[str, int], TModel],
            column: str = "id",
            return_models: bool = False,
    ) -> Union[List[TSchema], bool]:
        updates = {str(id): update for id, update in updates.items() if update}
        ids = list(updates.keys())
        db_models = await self.get_many_by_ids(
            session, ids=ids, column=column, with_for_update=True
        )

        for db_model in db_models:
            values = updates[str(getattr(db_model, column))].model_dump(
                exclude_unset=True
            )
            for k, v in values.items():
                setattr(db_model, k, v)
            session.add(db_model)

        try:
            await session.commit()
        except IntegrityError:
            raise IntegrityConflictException(
                f"{self.model.__tablename__} conflicts with existing data.",
            )

        if not return_models:
            return True

        for db_model in db_models:
            await session.refresh(db_model)

        return db_models

    async def remove_by_id(
            self,
            session: AsyncSession,
            id_: Union[str, int],
            column: str = "id",
    ) -> int:
        try:
            query = delete(self.model).where(getattr(self.model, column) == id_)
        except AttributeError:
            raise RepositoryException(
                f"Column {column} not found on {self.model.__tablename__}.",
            )

        rows = await session.execute(query)
        await session.commit()
        return rows.rowcount

    async def remove_many_by_ids(
            self,
            session: AsyncSession,
            ids: List[Union[str, int]],
            column: str = "id",
    ) -> int:
        if not ids:
            raise RepositoryException("No ids provided.")

        try:
            query = delete(self.model).where(getattr(self.model, column).in_(ids))
        except AttributeError:
            raise RepositoryException(
                f"Column {column} not found on {self.model.__tablename__}.",
            )

        rows = await session.execute(query)
        await session.commit()
        return rows.rowcount


def RepositoryFactory(model: Type[TSchema]) -> Type[BaseRepository[TModel, TSchema]]:
    return type(f'{model.__name__}Repository', (BaseRepository[TModel, TSchema],), {'model': model})
