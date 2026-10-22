# Local development services

This Compose file starts only the local dependencies used by the backend: PostgreSQL
for application data and Temporal's development server for durable workflows. The
Temporal development server stores its history at `/home/temporal/temporal.db` in the
`temporal_home_data` volume. This mounts over the image's UID 1000 user's home
directory so a fresh Docker volume is initialized with the correct ownership. Its
embedded store is for local development; it is separate from the PostgreSQL database
used by the application and is not a production Temporal deployment. All published
ports bind to `127.0.0.1` and are available only from the host machine.

The previous Compose configuration used a `temporal_data` volume at
`/var/lib/temporal`. The updated configuration creates a new volume; the old volume is
left untouched and can be removed after confirming its workflow history is no longer
needed.

Requirements: Docker Desktop (or Docker Engine with Compose v2), Python 3.12+, and
the backend dependencies installed from `backend/`.

From the repository root, start the services and wait for PostgreSQL to become healthy:

```powershell
docker compose -f infra/compose.yaml up -d
docker compose -f infra/compose.yaml ps
```

Temporal's UI is at <http://localhost:8233>. The API and workers connect to
`localhost:7233`.

Copy `backend/.env.example` to `backend/.env` once. Its local defaults match Compose.
Apply migrations from `backend/`:

```powershell
Set-Location backend
python -m pip install -e ".[dev]"
alembic upgrade head
python -m syncally.cli.seed_demo
```

Start each process in its own terminal, from `backend/`:

```powershell
python -m uvicorn syncally.api.main:app --reload
```

```powershell
python -m syncally.workflows.worker
```

```powershell
python -m syncally.cli.outbox_worker
```

The outbox relay starts or signals workflows only after their database events commit.
The workflow worker reloads business state from PostgreSQL when it receives a signal.
The seed command prompts for passwords for the local buyer and seller demo accounts.
For the browser, in a fourth terminal run `npm ci` and `npm run dev` from `frontend/`.

## Restart smoke test

With Compose services running and migrations applied, run the database-backed smoke
test from `backend/`. It uses an isolated PostgreSQL schema and the running Temporal
service; it does not touch the demo records or require the API process:

```powershell
$env:TEST_POSTGRES_URL = "postgresql+psycopg://syncally:syncally-local-only@127.0.0.1:5432/syncally"
$env:SYNCALLY_TEMPORAL_ADDRESS = "127.0.0.1:7233"
python -m unittest discover -s tests -p test_local_workflow_smoke.py -v
```

The test starts a workflow by relaying a persisted outbox notification, records
approval notifications, stops and restarts the worker, then verifies the workflow
processes notifications from Temporal history and that replaying the same agreement
commit creates no second commit, obligation, audit, or commit outbox event. It needs a
PostgreSQL user allowed to create schemas.

Stop the services while retaining their local data:

```powershell
docker compose -f infra/compose.yaml down
```

To discard the local database and workflow histories as well, run
`docker compose -f infra/compose.yaml down -v`.
