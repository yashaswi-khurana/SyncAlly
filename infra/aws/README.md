# AWS Temporal workers

`temporal-workers.yaml` deploys SyncAlly's workflow worker and outbox relay as ECS Fargate services; the separate payment worker is optional. `temporal-sandbox-data.yaml` creates a small PostgreSQL database, generated credentials, and worker/database security groups in an existing VPC. Temporal itself is managed by Temporal Cloud; these stacks do not create Temporal Server or the API service.

## Important: keep the Render API and AWS workers on one database

The frontend and backend API are already hosted on Render. The Render API and AWS workers must use the same PostgreSQL database because the API writes business state and outbox rows that the workers process. The `temporal-sandbox-data.yaml` stack creates a separate, empty RDS database; do **not** deploy it alongside the existing Render API as-is. First confirm where the Render API's current `DATABASE_URL` points.

If it points to Render Postgres, skip the RDS stack. Put Render's external PostgreSQL URL in an AWS Secrets Manager secret for the workers, use TLS, and configure Render Postgres to allow the workers' stable AWS egress IP. Fargate public IPs change when tasks are replaced, so a narrow allowlist requires private ECS subnets routed through a NAT gateway with an Elastic IP. This has additional recurring NAT and public-IP costs. See Render's [PostgreSQL connection guidance](https://render.com/docs/postgresql-creating-connecting) and AWS's [Fargate networking guide](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-task-networking.html).

If you intentionally migrate the shared database to AWS RDS, migrate the data and update the Render API to use that same database before starting workers. The current RDS template makes the database private; it does not establish a network path from Render. The deployment commands below describe that optional AWS-database path and must be adapted for Render-to-RDS connectivity before use.

## Prerequisites

- An ECR image built from `backend/Dockerfile`, pushed with an immutable tag or digest.
- For the sandbox template, an existing VPC and at least two subnets in different AZs. RDS is private. ECS tasks use public subnets with `AssignPublicIp=ENABLED` and no inbound security-group rules to reach Temporal Cloud without a NAT gateway. For production, use private ECS subnets, `AssignPublicIp=DISABLED`, and NAT or suitable VPC endpoints instead.
- The data stack creates a worker security group with no inbound rules and a database security group allowing PostgreSQL only from that worker group.
- Secrets Manager secret strings for the complete SQLAlchemy database URL, JWT signing secret, and Temporal Cloud API key. The data stack generates the DB password and JWT secret; the worker stack grants the ECS execution role read access only to the selected secret ARNs.
- A Temporal Cloud namespace and its endpoint/namespace identifier.

Before production, verify account quotas, image architecture (`linux/amd64` for this template), DB network reachability, secret encryption policies, and task sizing. The default workflow worker count is two. The outbox and payment services default to one; increase them only after load and concurrency/idempotency checks.

## Deploy

For the optional AWS-database path, deploy in three stages so no worker starts before the database schema is ready. These commands use the AWS account, ECR image, Temporal namespace, VPC, and two public subnets prepared for this sandbox. Run them from CloudShell in `us-east-1` after uploading this repository's `infra/aws` templates. The database stays private; the public IP setting applies only to outbound-only Fargate tasks. Do not run these commands for the existing Render database until migration and Render connectivity are planned.

### 1. Create the sandbox database and network rules

```bash
aws cloudformation deploy \
  --template-file infra/aws/temporal-sandbox-data.yaml \
  --stack-name syncally-sandbox-data \
  --parameter-overrides \
    VpcId=vpc-0d9c47a2d8fd1b1d2 \
    SubnetIds="subnet-033d8672a4527de04,subnet-0d6aaddf841d326fc"
```

Get the generated resource identifiers after the stack reaches `CREATE_COMPLETE`:

```bash
aws cloudformation describe-stacks --stack-name syncally-sandbox-data \
  --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' --output table
```

Record `WorkerSecurityGroupId`, `DatabaseUrlSecretArn`, and `JwtSecretArn`. The database master password and JWT signing secret are generated in Secrets Manager; neither value is printed by these commands.

### 2. Create the ECS cluster and task definitions, with services held back

Set the three values from the data stack outputs in your shell, then deploy the worker stack. Keep `DeployWorkerServices=false` for this initial deploy:

```bash
WORKER_SG=sg-OUTPUT_FROM_DATA_STACK
DATABASE_URL_SECRET=arn:aws:secretsmanager:us-east-1:577327405641:secret:OUTPUT_FROM_DATA_STACK
JWT_SECRET=arn:aws:secretsmanager:us-east-1:577327405641:secret:OUTPUT_FROM_DATA_STACK

aws cloudformation deploy \
  --template-file infra/aws/temporal-workers.yaml \
  --stack-name syncally-temporal-workers \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    SubnetIds="subnet-033d8672a4527de04,subnet-0d6aaddf841d326fc" \
    WorkerSecurityGroupId="$WORKER_SG" \
    ImageUri=577327405641.dkr.ecr.us-east-1.amazonaws.com/syncally/backend:workspace-20261106-01 \
    DatabaseUrlSecretArn="$DATABASE_URL_SECRET" \
    JwtSecretArn="$JWT_SECRET" \
    TemporalApiKeySecretArn=arn:aws:secretsmanager:us-east-1:577327405641:secret:syncally/temporal-cloud/api-key-4ozClB \
    TemporalAddress=quickstart-chanpreet-af7278b9.baq5d.tmprl.cloud:7233 \
    TemporalNamespace=quickstart-chanpreet-af7278b9.baq5d \
    PublicFrontendUrl=https://syncally-frontend.onrender.com \
    AssignPublicIp=ENABLED \
    WorkflowWorkerCount=1 \
    OutboxWorkerCount=1 \
    DeployPaymentWorker=false \
    DeployWorkerServices=false
```

The image is pinned by immutable ECR tag. For future releases, build and push a new tag, then pass that tag (or its digest) instead. Do not copy secret values into shell commands; only secret ARNs belong in the task parameters.

### 3. Run the Alembic migration as one task

The worker stack now has an ECS cluster and task definition but no continuously running worker services. Obtain `EcsClusterName`, `WorkflowTaskDefinition`, and `WorkerSecurityGroupId` from its outputs. Then run a one-off task with the same image and database secret, overriding only the command:

```bash
aws ecs run-task \
  --cluster syncally-temporal-workers-workers \
  --launch-type FARGATE \
  --task-definition TASK_DEFINITION_ARN_FROM_OUTPUT \
  --network-configuration 'awsvpcConfiguration={subnets=[subnet-033d8672a4527de04,subnet-0d6aaddf841d326fc],securityGroups=[sg-WORKER_FROM_OUTPUT],assignPublicIp=ENABLED}' \
  --overrides '{"containerOverrides":[{"name":"workflow-worker","command":["python","-m","alembic","upgrade","head"]}]}'
```

Use the **worker** security group output from the data stack. Wait for the task to stop and confirm its container exit code is `0` before proceeding. In the ECS console, open the task's CloudWatch log stream if it exits nonzero. Alembic requires only `DATABASE_URL`; the ECS task definition also injects the JWT and Temporal secrets, so the execution role must be able to read all three configured ARNs.

### 4. Start the workflow and outbox services

Update the same worker stack after the migration succeeds:

```bash
aws cloudformation deploy \
  --template-file infra/aws/temporal-workers.yaml \
  --stack-name syncally-temporal-workers \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides DeployWorkerServices=true
```

This starts one workflow worker and one outbox worker. Their logs go to `/syncally/syncally-temporal-workers/workers`. Check ECS service events and task logs, then verify in Temporal Cloud that the worker polls the `syncally-deals` task queue. The optional payment worker is separate from the Temporal path; enable it only after adding a Secrets Manager JSON secret with PayPal credentials and deploying with `DeployPaymentWorker=true` and `PaypalCredentialsSecretArn=...`.

The worker template can also be launched from the CloudFormation console by creating the data stack first, then the worker stack with the same parameter values and staged migration sequence.

The task CPU/memory and service counts can be overridden with CloudFormation parameters. To deploy PayPal Sandbox credentials, pass `PaypalCredentialsSecretArn` for a Secrets Manager JSON secret containing `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, and `PAYPAL_WEBHOOK_ID`. Leave it empty to run the payment worker without provider credentials; it will not be able to dispatch PayPal invoices.

The worker stack creates an ECS cluster and task definitions on the initial deploy; the workflow and outbox services are created only when `DeployWorkerServices=true`. It also creates a scoped execution role, an application task role, and a CloudWatch log group. It can optionally create the payment worker. The sandbox data stack creates the PostgreSQL database, database subnet group, generated DB password and JWT secrets, database URL secret, and security groups. Neither stack creates a VPC, subnets, NAT gateways, the API service, or Temporal Cloud resources. Do not place credentials in command history or commit them to this repository; pass only secret ARNs as parameters.

## Verify and update

Check ECS service events and task status in the AWS console, then inspect the log streams under `/syncally/<stack-name>/workers`. Confirm the workflow worker logs a successful start, the outbox worker can connect to Temporal and PostgreSQL, and a staging deal progresses through the task queue. Roll out the same immutable image to all relevant services. Updating a Secrets Manager value requires new tasks to be started; force a new ECS deployment after rotation. The sandbox's public ECS IPs are charged hourly and should be removed by scaling tasks to zero or deleting the stack when finished.

Use CloudFormation stack updates for later changes. Scale the workflow worker service to at least two replicas across Availability Zones for production. A `RUNNING` task is only process-level evidence; alert on outbox age, queue latency, activity failures, and payment backlog as described in [the deployment guide](../../docs/aws-temporal-deployment.md).
