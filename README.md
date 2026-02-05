# hitl

HITL Credit Approval System.

## Docs
- `hitl/prd.md`
- `hitl/todo.md`
- `hitl/changelog.md`

## Local dev (minimal)
```bash
cp .env.example .env
docker compose up --build
# API: http://localhost:8000/health
```

## Migrations
Run inside the api container:
```bash
docker compose run --rm api alembic upgrade head
```

## Dev seed data
If you want a quick demo tenant + users + default active threshold in your local DB, run:
```bash
docker compose run --rm \
  -e DATABASE_URL="postgresql+asyncpg://hitl:hitl_dev_password@postgres/hitl_credit" \
  api python -m src.scripts.seed_dev_data
```

This is idempotent (safe to run multiple times).
