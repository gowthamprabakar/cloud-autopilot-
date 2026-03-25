"""
Generic async repository base.

Provides standard CRUD operations. All domain repositories extend this.
Never contains business logic — only data access.
"""

import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, id: uuid.UUID) -> ModelT | None:
        result = await self.db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_by_id_or_raise(self, id: uuid.UUID) -> ModelT:
        from app.core.exceptions import NotFoundError
        obj = await self.get_by_id(id)
        if obj is None:
            raise NotFoundError(f"{self.model.__name__} {id} not found")
        return obj

    async def create(self, obj: ModelT) -> ModelT:
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update_fields(self, id: uuid.UUID, **fields: Any) -> ModelT:
        await self.db.execute(
            update(self.model).where(self.model.id == id).values(**fields)
        )
        await self.db.flush()
        return await self.get_by_id_or_raise(id)

    async def delete(self, id: uuid.UUID) -> None:
        obj = await self.get_by_id_or_raise(id)
        await self.db.delete(obj)
        await self.db.flush()
