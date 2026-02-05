"""Seed development data.

This script is intentionally lightweight and idempotent-ish: it creates a demo tenant,
a couple of users, an active decision threshold, and a handful of sample applications.

Usage:
  python -m src.scripts.seed_dev_data

Notes:
- We do not run this locally in OpenClaw runtime; CI/devs can run it against a dev DB.
- Uses DATABASE_URL from settings (or env via pydantic settings).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from src.database import SessionLocal
from src.models.application import Application
from src.models.decision_threshold import DecisionThreshold
from src.models.tenant import Tenant
from src.models.user import User


DEMO_TENANT_SLUG = "demo"
DEMO_TENANT_NAME = "Demo Tenant"


async def _get_or_create_demo_tenant() -> Tenant:
    async with SessionLocal() as session:
        existing = await session.scalar(select(Tenant).where(Tenant.slug == DEMO_TENANT_SLUG))
        if existing:
            return existing

        tenant = Tenant(
            name=DEMO_TENANT_NAME,
            slug=DEMO_TENANT_SLUG,
            settings={"seeded": True},
            subscription_tier="standard",
            is_active=True,
        )
        session.add(tenant)
        await session.commit()
        await session.refresh(tenant)
        return tenant


async def _get_or_create_user(*, tenant_id, email: str, role: str, first_name: str, last_name: str) -> User:
    async with SessionLocal() as session:
        existing = await session.scalar(
            select(User).where(User.tenant_id == tenant_id, User.email == email)
        )
        if existing:
            return existing

        user = User(
            tenant_id=tenant_id,
            email=email,
            password_hash=None,
            first_name=first_name,
            last_name=last_name,
            role=role,
            permissions=[],
            preferences={"seeded": True},
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def _ensure_active_threshold(*, tenant_id, created_by) -> DecisionThreshold:
    now = datetime.now(tz=UTC)

    async with SessionLocal() as session:
        # If there's already an active threshold, keep it.
        existing_active = await session.scalar(
            select(DecisionThreshold).where(
                DecisionThreshold.tenant_id == tenant_id,
                DecisionThreshold.is_active.is_(True),
            )
        )
        if existing_active:
            return existing_active

        threshold = DecisionThreshold(
            tenant_id=tenant_id,
            name="Default",
            description="Seeded default threshold configuration",
            auto_approve_min=720,
            auto_decline_max=540,
            rules={
                "max_loan_amount_auto": 50000,
                "max_term_months_auto": 60,
                "require_review_purposes": ["business", "debt_consolidation"],
            },
            is_active=True,
            effective_from=now,
            effective_to=None,
            created_by=created_by,
            approved_by=created_by,
        )
        session.add(threshold)
        await session.commit()
        await session.refresh(threshold)
        return threshold


async def _seed_applications(*, tenant_id) -> int:
    async with SessionLocal() as session:
        existing_count = await session.scalar(
            select(func.count()).select_from(Application).where(Application.tenant_id == tenant_id)
        )
        # If there are already applications, do not spam more.
        if existing_count and existing_count > 0:
            return 0

        now = datetime.now(tz=UTC)

        apps: list[Application] = []
        for i in range(1, 6):
            apps.append(
                Application(
                    tenant_id=tenant_id,
                    external_id=f"DEMO-{i:05d}",
                    status="pending",
                    applicant_data={
                        "personal": {
                            "first_name": "Demo",
                            "last_name": f"Applicant{i}",
                            "email": f"demo{i}@example.com",
                        }
                    },
                    financial_data={
                        "net_monthly_income": 2500 + (i * 250),
                        "monthly_obligations": 600 + (i * 50),
                        "existing_loans_payment": 200,
                    },
                    loan_request={
                        "loan_amount": 5000 * i,
                        "term_months": 24,
                        "purpose": "personal",
                    },
                    credit_bureau_data=None,
                    source="seed",
                    meta={"seeded": True},
                    submitted_at=now - timedelta(days=6 - i),
                    expires_at=now + timedelta(days=30),
                )
            )

        session.add_all(apps)
        await session.commit()
        return len(apps)


async def main() -> None:
    tenant = await _get_or_create_demo_tenant()

    admin = await _get_or_create_user(
        tenant_id=tenant.id,
        email="admin@demo.local",
        role="admin",
        first_name="Demo",
        last_name="Admin",
    )
    await _get_or_create_user(
        tenant_id=tenant.id,
        email="analyst@demo.local",
        role="analyst",
        first_name="Demo",
        last_name="Analyst",
    )

    await _ensure_active_threshold(tenant_id=tenant.id, created_by=admin.id)
    created = await _seed_applications(tenant_id=tenant.id)

    print(
        "Seed complete:",
        {
            "tenant_slug": tenant.slug,
            "admin_email": admin.email,
            "applications_created": created,
        },
    )


if __name__ == "__main__":
    asyncio.run(main())
