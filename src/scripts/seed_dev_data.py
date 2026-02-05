from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import settings
from src.models.decision_threshold import DecisionThreshold
from src.models.tenant import Tenant
from src.models.user import User


@dataclass(frozen=True)
class SeedUserSpec:
    email: str
    role: str
    first_name: str
    last_name: str


DEMO_TENANT_SLUG = "demo"
DEMO_TENANT_NAME = "Demo Tenant"

DEMO_USERS: tuple[SeedUserSpec, ...] = (
    SeedUserSpec(email="admin@demo.local", role="admin", first_name="Demo", last_name="Admin"),
    SeedUserSpec(email="analyst@demo.local", role="analyst", first_name="Demo", last_name="Analyst"),
    SeedUserSpec(email="senior@demo.local", role="senior_analyst", first_name="Demo", last_name="Senior"),
)


async def _get_or_create_tenant(session: AsyncSession) -> Tenant:
    res = await session.execute(select(Tenant).where(Tenant.slug == DEMO_TENANT_SLUG))
    tenant = res.scalar_one_or_none()

    if tenant is None:
        tenant = Tenant(name=DEMO_TENANT_NAME, slug=DEMO_TENANT_SLUG, settings={}, subscription_tier="standard")
        session.add(tenant)
        await session.flush()
    else:
        # Keep it idempotent but allow evolving defaults.
        tenant.name = tenant.name or DEMO_TENANT_NAME
        tenant.is_active = True

    return tenant


async def _get_or_create_user(session: AsyncSession, *, tenant_id, spec: SeedUserSpec) -> User:
    res = await session.execute(
        select(User).where(User.tenant_id == tenant_id, User.email == spec.email)
    )
    user = res.scalar_one_or_none()

    if user is None:
        user = User(
            tenant_id=tenant_id,
            email=spec.email,
            role=spec.role,
            first_name=spec.first_name,
            last_name=spec.last_name,
            # NOTE: auth not implemented yet; keep nullable for now.
            password_hash=None,
            permissions=[],
            preferences={},
            is_active=True,
        )
        session.add(user)
        await session.flush()
    else:
        # Ensure the demo users stay active and roles are as expected.
        user.is_active = True
        user.role = spec.role
        user.first_name = user.first_name or spec.first_name
        user.last_name = user.last_name or spec.last_name

    return user


async def _ensure_default_threshold(session: AsyncSession, *, tenant_id, created_by_user_id) -> DecisionThreshold:
    """Ensure there is a single active default threshold for the demo tenant.

    We intentionally keep this simple and deterministic for local dev.
    """

    # Prefer an existing active threshold if present.
    res = await session.execute(
        select(DecisionThreshold)
        .where(DecisionThreshold.tenant_id == tenant_id, DecisionThreshold.is_active.is_(True))
        .order_by(DecisionThreshold.effective_from.desc())
        .limit(1)
    )
    active = res.scalar_one_or_none()
    if active is not None:
        return active

    # Otherwise, create one and leave any historical thresholds inactive.
    now = datetime.now(timezone.utc)
    threshold = DecisionThreshold(
        tenant_id=tenant_id,
        name="Default (dev)",
        description="Default decision routing thresholds for local development.",
        auto_approve_min=650,
        auto_decline_max=450,
        rules={
            "max_loan_amount_auto": 25000,
            "max_term_months_auto": 60,
            "require_review_purposes": ["debt_consolidation", "business"],
        },
        is_active=True,
        effective_from=now,
        effective_to=None,
        created_by=created_by_user_id,
        approved_by=created_by_user_id,
    )
    session.add(threshold)
    await session.flush()
    return threshold


async def seed_dev_data() -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with session_maker() as session:
        async with session.begin():
            tenant = await _get_or_create_tenant(session)

            users: list[User] = []
            for spec in DEMO_USERS:
                users.append(await _get_or_create_user(session, tenant_id=tenant.id, spec=spec))

            admin = next(u for u in users if u.role == "admin")
            await _ensure_default_threshold(session, tenant_id=tenant.id, created_by_user_id=admin.id)

    await engine.dispose()


def main() -> None:
    asyncio.run(seed_dev_data())


if __name__ == "__main__":
    main()
