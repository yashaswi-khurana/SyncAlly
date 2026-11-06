# Free single-VM deployment

This stack runs SyncAlly's frontend, API, PostgreSQL, Temporal Server, workflow
worker, outbox worker, and payment worker on one OCI Ampere VM. Caddy serves the
frontend and API on `APP_DOMAIN`, obtains HTTPS certificates, and forwards the
Temporal gRPC endpoint on `TEMPORAL_DOMAIN` only for callers on the private Docker
network. Database and Temporal ports are not published to the internet.

This is a low-cost demo/staging layout, not a highly available production cluster:
the VM is one failure point. Keep database backups outside the VM if the data
matters. OCI's Always Free A1 allowance is up to 2 OCPUs and 12 GB RAM, subject to
home-region capacity. Oracle says Free Tier resources are not charged unless the
account is upgraded; idle Always Free instances may be reclaimed. See [Always Free
resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
and [Free Tier account terms](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm).

## 1. Provision the VM and DNS

The OCI account owner should create an Always Free eligible `VM.Standard.A1.Flex`
Ubuntu ARM64 VM, using no more than 2 OCPUs and 12 GB RAM. The owner may need a
payment card to verify the OCI account; never share the card or OCI password. A
free DNS provider or an existing domain is sufficient.

Assign a stable public IPv4 address. Create two DNS A records pointing to it, for
example `syncally.example.com` and `temporal.example.com`. In the VM's network
security list and its host firewall, allow inbound TCP 80 and 443. Limit SSH (TCP
22) to the administrator's current IP. Do not open ports 5432 or 7233. The public
`TEMPORAL_DOMAIN` hostname returns 404 to clients outside the Docker network.

Install Docker Engine and the Compose plugin using Docker's [official Ubuntu
instructions](https://docs.docker.com/engine/install/ubuntu/). Then clone the
repository after both the customer-journey and deployment changes are merged to
`main`:

```sh
git clone https://github.com/yashaswi-khurana/SyncAlly.git
cd SyncAlly
```

## 2. Configure secrets

Copy the template and generate four separate values by running `openssl rand -hex 32` four times:

```sh
cp infra/deploy/.env.example infra/deploy/.env
openssl rand -hex 32
```

Put unique generated values in `POSTGRES_ADMIN_PASSWORD`, `SYNCALLY_DB_PASSWORD`,
`TEMPORAL_DB_PASSWORD`, and `JWT_SECRET`. Set `APP_DOMAIN` and `TEMPORAL_DOMAIN`
to the DNS records above. Keep `infra/deploy/.env` private; it is ignored by Git.

The default keeps AI offline and payment in PayPal Sandbox mode. To enable sandbox
invoices, add PayPal Sandbox app credentials. Gmail invoice copies and OpenAI
assistance are optional. Do not put production PayPal credentials into this demo
deployment.

## 3. Start the stack

From the repository root:

```sh
docker compose --env-file infra/deploy/.env -f infra/deploy/compose.yaml config --quiet
docker compose --env-file infra/deploy/.env -f infra/deploy/compose.yaml up -d --build
docker compose --env-file infra/deploy/.env -f infra/deploy/compose.yaml ps
```

The first start creates the database roles and Temporal schemas, runs the SyncAlly
Alembic migrations, creates Temporal's `default` namespace, then starts the API and
workers. Caddy can issue certificates once both DNS records resolve to the VM and
ports 80 and 443 are reachable. Open `https://<APP_DOMAIN>` to use SyncAlly. Inside
Docker, `TEMPORAL_DOMAIN` resolves to Caddy on the private Compose network; Caddy
forwards gRPC to the private Temporal container. It is not a browser page.

Use these commands to inspect startup and service logs:

```sh
docker compose --env-file infra/deploy/.env -f infra/deploy/compose.yaml ps
docker compose --env-file infra/deploy/.env -f infra/deploy/compose.yaml logs --tail=100 web api temporal workflow-worker outbox-worker payment-worker
```

Create the first user through the app's sign-up flow. Do not run the local demo
seeder against this database.

## Updating and operating

Back up PostgreSQL before deploying schema changes. Then pull `main`, rebuild, and
restart the services with the same `docker compose ... up -d --build` command.
Compose retains the database and Caddy certificates in named volumes. To stop the
stack without deleting data, use `docker compose ... down`; **do not** add `-v`
unless you intend to delete all database and certificate volumes.

This guide cannot provision the VM or validate the live DNS/TLS path without the
OCI account owner's access. After that owner completes account verification and
VM setup, the remaining commands above can be run over SSH.
