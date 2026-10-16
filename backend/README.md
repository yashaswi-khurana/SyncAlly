# SyncAlly backend

Python package for the HTTP API, application use cases, domain rules, adapters, and durable workflow processes.

The API remains a health-endpoint shell. The domain package now contains framework-independent foundations for deals, negotiation, canonical trade terms, bilateral agreement approval, and payment intent state. Database access, application command handlers, workflows, authentication, and provider integrations are not implemented.

Install from the repository root with `python -m pip install -e ./backend`.

See [the domain architecture](../docs/architecture/05-domain-layer.md) for implemented invariants, package boundaries, and remaining work. The domain types do not perform persistence, authenticated authorization, or external provider calls.
