# SyncAlly backend

Python package for the HTTP API, application use cases, domain rules, adapters, and durable workflow processes.

The current implementation is intentionally small: `syncally.api.main:app` provides a health endpoint. Database access, workflows, authentication, and provider integrations are not implemented.

Install from the repository root with `python -m pip install -e ./backend`.
