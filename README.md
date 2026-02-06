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
