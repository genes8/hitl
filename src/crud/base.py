from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseCRUD(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Generic async CRUD helper.

    Notes:
    - This is intentionally lightweight: endpoints/services can opt into explicit
      transaction control by passing commit=False.
    - Tenant isolation is supported via `tenant_id` filtering when the model
      includes a `tenant_id` attribute.
    """

    def __init__(self, model: type[ModelType]):
        self.model = model

    async def create(
        self,
        session: AsyncSession,
        *,
        obj_in: CreateSchemaType | dict[str, Any],
        commit: bool = True,
    ) -> ModelType:
        data = obj_in if isinstance(obj_in, dict) else obj_in.model_dump()
        db_obj = self.model(**data)  # type: ignore[arg-type]
        session.add(db_obj)
        await session.flush()

        if commit:
            await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def get(
        self,
        session: AsyncSession,
        *,
        id: Any,
        tenant_id: Any | None = None,
    ) -> ModelType | None:
        q = select(self.model).where(self.model.id == id)  # type: ignore[attr-defined]
        if tenant_id is not None and hasattr(self.model, "tenant_id"):
            q = q.where(self.model.tenant_id == tenant_id)  # type: ignore[attr-defined]
        r = await session.execute(q)
        return r.scalar_one_or_none()

    async def get_multi(
        self,
        session: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        tenant_id: Any | None = None,
        filters: list[Any] | None = None,
    ) -> list[ModelType]:
        q = select(self.model)
        if tenant_id is not None and hasattr(self.model, "tenant_id"):
            q = q.where(self.model.tenant_id == tenant_id)  # type: ignore[attr-defined]
        if filters:
            for f in filters:
                q = q.where(f)
        q = q.offset(skip).limit(limit)
        r = await session.execute(q)
        return list(r.scalars().all())

    async def update(
        self,
        session: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any],
        commit: bool = True,
    ) -> ModelType:
        data = (
            obj_in
            if isinstance(obj_in, dict)
            else obj_in.model_dump(exclude_unset=True)
        )

        for field, value in data.items():
            setattr(db_obj, field, value)

        session.add(db_obj)
        await session.flush()

        if commit:
            await session.commit()
        await session.refresh(db_obj)
        return db_obj

    async def delete(
        self,
        session: AsyncSession,
        *,
        id: Any,
        tenant_id: Any | None = None,
        commit: bool = True,
    ) -> ModelType | None:
        obj = await self.get(session=session, id=id, tenant_id=tenant_id)
        if obj is None:
            return None

        await session.delete(obj)  # type: ignore[arg-type]
        await session.flush()

        if commit:
            await session.commit()
        return obj
