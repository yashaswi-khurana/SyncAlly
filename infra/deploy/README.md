# SyncAlly deployment

## Current $0 demo: Render + Hostless

Reuse the existing Render static site and `syncally-db` PostgreSQL instance. Deploy
one Hostless App from this repository using the root `hostless.yaml`; it runs the
API, Temporal CLI development server, workflow worker, outbox worker, payment
worker, and Slack Events worker together. Do not create another database, worker,
or persistent volume for this layout. `hostless.yaml` caps the app at 0.5 vCPU and 1 GiB RAM, matching the
published shared free pool; check the account's own billing page before creating
the resource and stop if the UI says it needs a paid plan or billing method.

The Temporal server listens only on `127.0.0.1:7233`, so its plaintext gRPC
connection never leaves the Hostless app. Its state file is under `/tmp`; Hostless
does not preserve that directory across restarts. This is a demo/staging layout,
not a durable production Temporal deployment. Render's free Postgres also expires
after its free lifetime. See the [Render free instance limits](https://render.com/docs/free)
and [Hostless free limits](https://docs.hostless.cloud/plans/free-tier).

### Configure the Hostless App

Create an App from `yashaswi-khurana/SyncAlly` on branch
`codex/free-demo-deployment`. Use the repository root and the checked-in
`hostless.yaml`; do not attach storage. Add these runtime variables in Hostless:

```text
APP_ENV=production
DATABASE_URL=<External Database URL from the existing Render syncally-db>
JWT_SECRET=<new random secret of at least 32 random bytes>
PUBLIC_FRONTEND_URL=https://syncally-frontend.onrender.com
TEMPORAL_ADDRESS=127.0.0.1:7233
TEMPORAL_TLS=false
TEMPORAL_NAMESPACE=default
TEMPORAL_TASK_QUEUE=syncally-deals
AI_PROVIDER=offline
AI_REMOTE_EGRESS_ENABLED=false
AI_REMOTE_ALLOW_PRIVATE=false
AI_REMOTE_PRIVATE_ORGANIZATION_IDS=[]
GOOGLE_API_KEY=
GEMINI_MODEL=
PAYMENT_MODE=PAYPAL_SANDBOX
```

Use Render's external database URL, including its TLS query parameter. Treat it
and `JWT_SECRET` as secrets. The backend permits plaintext Temporal only for a
loopback address; remote Temporal endpoints still require TLS. The container runs
the migrations before serving the API.

### Connect the Render frontend

After Hostless reports the app as healthy, copy its HTTPS URL into the Render
static site's `VITE_API_BASE_URL` environment variable and redeploy the site. The
backend's CORS allowlist is restricted to `PUBLIC_FRONTEND_URL`.

Verify `GET /health`, `GET /health/database`, and the Hostless logs for all three
worker start messages. Do not seed demo data into the shared database. PayPal
actions need PayPal Sandbox credentials; invitations currently return a link for
manual sharing rather than sending email.

## OCI single-VM deployment

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
