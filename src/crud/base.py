from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


TModel = TypeVar("TModel")
TCreate = TypeVar("TCreate")
TUpdate = TypeVar("TUpdate")


def _to_dict(obj: Any, *, exclude_unset: bool = True) -> dict[str, Any]:
    """Best-effort conversion for Pydantic models / plain dict payloads."""

    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, BaseModel):
        # Pydantic v2
        if hasattr(obj, "model_dump"):
            return obj.model_dump(exclude_unset=exclude_unset)
        # Pydantic v1 fallback
        return obj.dict(exclude_unset=exclude_unset)  # type: ignore[attr-defined]

    # Last resort: try vars()
    return dict(vars(obj))


class BaseCRUD(Generic[TModel, TCreate, TUpdate]):
    """Generic CRUD helper for SQLAlchemy (async).

    Notes:
    - Methods intentionally do NOT commit. Callers control transaction boundaries.
    - Tenant filtering is opt-in via tenant_id parameter.

    This is a lightweight v1 scaffold to support the TODO in hitl/todo.md.
    """

    def __init__(
        self,
        model: type[TModel],
        *,
        tenant_field: str = "tenant_id",
    ) -> None:
        self.model = model
        self.tenant_field = tenant_field

    async def create(
        self,
        session: AsyncSession,
        *,
        obj_in: TCreate,
        tenant_id: Any | None = None,
    ) -> TModel:
        data = _to_dict(obj_in)
        if tenant_id is not None and self.tenant_field not in data:
            data[self.tenant_field] = tenant_id

        db_obj = self.model(**data)  # type: ignore[call-arg]
        session.add(db_obj)
        await session.flush()
        return db_obj

    async def get(
        self,
        session: AsyncSession,
        *,
        id: Any,
        tenant_id: Any | None = None,
    ) -> TModel | None:
        q = select(self.model).where(getattr(self.model, "id") == id)
        if tenant_id is not None and hasattr(self.model, self.tenant_field):
            q = q.where(getattr(self.model, self.tenant_field) == tenant_id)

        r = await session.execute(q)
        return r.scalar_one_or_none()

    async def get_multi(
        self,
        session: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        tenant_id: Any | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[TModel]:
        q = select(self.model)

        if tenant_id is not None and hasattr(self.model, self.tenant_field):
            q = q.where(getattr(self.model, self.tenant_field) == tenant_id)

        if filters:
            for key, value in filters.items():
                if value is None:
                    continue
                if not hasattr(self.model, key):
                    continue
                q = q.where(getattr(self.model, key) == value)

        q = q.offset(max(skip, 0)).limit(max(1, limit))
        r = await session.execute(q)
        return list(r.scalars().all())

    async def update(
        self,
        session: AsyncSession,
        *,
        db_obj: TModel,
        obj_in: TUpdate,
    ) -> TModel:
        data = _to_dict(obj_in)

        for field, value in data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        session.add(db_obj)  # no-op for persistent objects, safe for detached
        await session.flush()
        return db_obj

    async def delete(
        self,
        session: AsyncSession,
        *,
        id: Any,
        tenant_id: Any | None = None,
    ) -> TModel | None:
        obj = await self.get(session, id=id, tenant_id=tenant_id)
        if obj is None:
            return None

        await session.delete(obj)  # type: ignore[arg-type]
        await session.flush()
        return obj
