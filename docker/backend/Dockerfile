FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
  && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir -U pip \
  && pip install --no-cache-dir \
    fastapi==0.109.* \
    uvicorn[standard]==0.27.* \
    pydantic-settings==2.5.* \
    sqlalchemy==2.0.* \
    asyncpg==0.29.* \
    psycopg[binary]==3.1.* \
    alembic==1.13.* \
    celery[redis]==5.3.* \
    pytest==8.* \
    httpx==0.27.*

COPY src ./src

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
