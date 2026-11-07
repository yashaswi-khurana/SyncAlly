FROM temporalio/temporal:1.9.1 AS temporal-cli

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=temporal-cli /usr/local/bin/temporal /usr/local/bin/temporal
COPY backend/pyproject.toml backend/README.md ./
COPY backend/src ./src
COPY backend/alembic.ini ./alembic.ini
COPY backend/alembic ./alembic
COPY infra/deploy/hostless-start.sh ./infra/deploy/hostless-start.sh

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir . \
    && chmod +x /app/infra/deploy/hostless-start.sh

EXPOSE 8000

CMD ["/app/infra/deploy/hostless-start.sh"]
