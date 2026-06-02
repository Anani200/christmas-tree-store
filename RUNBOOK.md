# Runbook — Local Testing & AWS Deployment

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.12 | `pyenv install 3.12` or system package |
| Node.js | 18 | `nvm install 18` |
| npm | 9+ | bundled with Node 18 |
| Docker | 24+ | https://docs.docker.com/get-docker/ |
| AWS CLI | v2 | https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html |
| AWS SAM CLI | 1.120+ | https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html |

Verify everything is installed:

```bash
python3 --version   # Python 3.12.x
node --version      # v18.x.x
docker --version    # Docker 24.x
aws --version       # aws-cli/2.x
sam --version       # SAM CLI, version 1.x
```

---

## Part 1 — Local Testing

### 1.1 Clone & root setup

```bash
git clone <repo-url> christmas-tree-store
cd christmas-tree-store
```

### 1.2 Backend — install deps and run tests

```bash
cd backend
python3.12 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements-dev.txt
```

Run all 52 unit tests (no AWS credentials needed):

```bash
.venv/bin/python -m pytest tests/ -v
```

Expected output: **52 passed**. The `LOCAL_MOCK=true` flag is set automatically for the handler tests — no real DynamoDB, SQS, or Cognito calls are made.

Run linter and type checker:

```bash
.venv/bin/ruff check src/
.venv/bin/mypy src/
```

### 1.3 Frontend — install deps and run tests

```bash
cd ../frontend
npm install
```

Run all 9 component/unit tests (no AWS credentials needed):

```bash
npm test
```

Expected output: **9 passed** (2 test files).

Type-check and build:

```bash
npx tsc -b         # must produce no output (zero type errors)
npm run build      # must end with "built in Xs"
```

The compiled SPA lands in `frontend/dist/`.

### 1.4 Start DynamoDB Local (Docker)

```bash
cd ..   # repo root
docker compose up -d
```

Wait for the health check to go green (usually < 5 s), then confirm it's alive:

```bash
curl -s http://localhost:8000/ | head -c 80
```

Any response (even an empty object `{}`) confirms the container is up.

### 1.5 Create local tables and seed products

This script creates both DynamoDB Local tables and inserts the 5 seed products:

```bash
chmod +x scripts/setup-local.sh
./scripts/setup-local.sh
```

Expected output ends with: `✓ Local setup complete.`

Verify the products were written:

```bash
aws dynamodb scan \
  --endpoint-url http://localhost:8000 \
  --table-name christmas-tree-store-products \
  --region us-east-1 \
  --no-cli-pager \
  --query "Count"
```

Should print `5`.

### 1.6 Create a local environment file for the API Lambda

Create `local-env.json` at the repo root (never committed — it is in `.gitignore`):

```json
{
  "OrderApiFunction": {
    "PRODUCTS_TABLE": "christmas-tree-store-products",
    "ORDERS_TABLE": "christmas-tree-store-orders",
    "ORDER_QUEUE_URL": "http://localhost:4566/000000000000/christmas-tree-store-orders",
    "CORS_ALLOWED_ORIGIN": "http://localhost:5173",
    "DDB_ENDPOINT": "http://localhost:8000",
    "LOCAL_MOCK": "false"
  },
  "AuthFunction": {
    "USER_POOL_ID": "us-east-1_placeholder",
    "USER_POOL_CLIENT_ID": "placeholder",
    "CORS_ALLOWED_ORIGIN": "http://localhost:5173",
    "LOCAL_MOCK": "true"
  },
  "NotificationFunction": {
    "PRODUCTS_TABLE": "christmas-tree-store-products",
    "ORDERS_TABLE": "christmas-tree-store-orders",
    "ORDER_NOTIFICATIONS_TOPIC_ARN": "arn:aws:sns:us-east-1:000000000000:placeholder",
    "LOCAL_MOCK": "true"
  }
}
```

> **Tip:** Set `"LOCAL_MOCK": "true"` on `OrderApiFunction` too if you just want to exercise the API without Docker running. Seed data is served from memory. Auth calls always return mock tokens when `LOCAL_MOCK=true` on `AuthFunction`.

### 1.7 Start the local API (SAM)

```bash
cd infra
sam build
sam local start-api \
  --env-vars ../local-env.json \
  --port 3000
```

SAM will rebuild the Lambda image on first start (one-time pull, ~30 s). Keep this terminal open.

Test the API in a second terminal:

```bash
# Health check
curl http://localhost:3000/health

# List all products
curl http://localhost:3000/products

# Single product
curl http://localhost:3000/products/tree-001

# Register (mock — LOCAL_MOCK=true returns stub response)
curl -s -X POST http://localhost:3000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Pass1234"}'

# Login (mock — returns mock tokens)
curl -s -X POST http://localhost:3000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Pass1234"}'

# Place a (mocked) order — skip auth header when LOCAL_MOCK=true
curl -s -X POST http://localhost:3000/orders \
  -H "Content-Type: application/json" \
  -d '{
    "productId": "tree-001",
    "quantity": 1,
    "customerName": "Test User",
    "customerEmail": "test@example.com",
    "customerPhone": "555-000-0001",
    "preferredPickupDate": "2026-12-20"
  }'
```

Expected responses: `200` for GET routes, `201` for POST /auth/register and POST /orders.

### 1.8 Start the frontend dev server

```bash
cd frontend
cp .env.local.example .env.local
```

Edit `.env.local` with the local values (Cognito values are not needed when using the API in mock mode):

```
VITE_API_URL=http://localhost:3000
VITE_USER_POOL_ID=us-east-1_placeholder
VITE_USER_POOL_CLIENT_ID=placeholder
VITE_REGION=us-east-1
```

Start the dev server:

```bash
npm run dev
```

Open http://localhost:5173 — you should see the Christmas tree catalog populated from the local API.

### 1.9 Tear down local environment

```bash
# Stop DynamoDB Local
docker compose down

# Stop SAM (Ctrl-C in that terminal)

# Stop frontend dev server (Ctrl-C)
```

---

## Part 2 — AWS Deployment

### 2.1 Configure AWS credentials

```bash
aws configure
# AWS Access Key ID:     <your key>
# AWS Secret Access Key: <your secret>
# Default region:        us-east-1
# Default output format: json
```

Verify:

```bash
aws sts get-caller-identity
```

The account ID and ARN must be returned (no error).

### 2.2 Build the SAM application

```bash
cd infra
sam build
```

SAM compiles each Lambda with its dependencies and caches the result in `.aws-sam/`.

### 2.3 Deploy the infrastructure (first time — guided)

```bash
sam deploy --guided
```

Answer the prompts:

| Prompt | Recommended value |
|--------|-------------------|
| Stack name | `christmas-tree-store` |
| AWS Region | `us-east-1` |
| Parameter ProjectName | `christmas-tree-store` |
| Parameter RetailerEmail | `owner@example.com` *(your email — leave blank to skip)* |
| Parameter CorsAllowedOrigin | `http://localhost:5173` *(update after step 2.5)* |
| Confirm changes before deploy | `y` |
| Allow SAM to create IAM roles | `y` |
| Disable rollback | `N` |
| Save config to `samconfig.toml` | `y` |

SAM will create the CloudFormation change set, show you a summary, then deploy ~13 resources. The first deploy takes about 3–5 minutes.

Subsequent deploys (after code changes):

```bash
sam build && sam deploy
```

### 2.4 Retrieve stack outputs

```bash
aws cloudformation describe-stacks \
  --stack-name christmas-tree-store \
  --region us-east-1 \
  --query "Stacks[0].Outputs" \
  --output table
```

Note these values — you'll need them for the next steps:

- `CloudFrontUrl` — the HTTPS URL of your site (e.g. `https://d1abc123.cloudfront.net`)
- `ApiUrl` — API Gateway invoke URL
- `UserPoolId` — Cognito User Pool ID
- `UserPoolClientId` — Cognito App Client ID
- `FrontendBucketName` — S3 bucket name for the SPA

### 2.5 Confirm SNS email subscription (if RetailerEmail was set)

Check the inbox of the retailer email address. You will receive an email with subject **"AWS Notification — Subscription Confirmation"**. Click the link to confirm. All new orders will now trigger an email notification.

### 2.6 Update CORS to the CloudFront URL

Now that you have the real CloudFront URL, update the SAM parameter:

```bash
sam deploy \
  --parameter-overrides \
    "CorsAllowedOrigin=https://d1abc123.cloudfront.net"
```

Replace `d1abc123.cloudfront.net` with your actual value from step 2.4.

### 2.7 Seed products into the live DynamoDB table

```bash
cd backend
PRODUCTS_TABLE=christmas-tree-store-products \
AWS_DEFAULT_REGION=us-east-1 \
  .venv/bin/python -m src.seed.run
```

Verify:

```bash
aws dynamodb scan \
  --table-name christmas-tree-store-products \
  --region us-east-1 \
  --no-cli-pager \
  --query "Count"
```

Should print `5`.

### 2.8 Build and deploy the React frontend

Create the production environment file:

```bash
cd frontend
cat > .env.production.local << 'EOF'
VITE_API_URL=https://d1abc123.cloudfront.net
VITE_USER_POOL_ID=us-east-1_XXXXXXXXX
VITE_USER_POOL_CLIENT_ID=XXXXXXXXXXXXXXXXXXXXXXXXXX
VITE_REGION=us-east-1
EOF
```

Replace placeholders with the values from step 2.4.

Build the production bundle:

```bash
npm run build
```

Upload to S3:

```bash
BUCKET=$(aws cloudformation describe-stacks \
  --stack-name christmas-tree-store \
  --region us-east-1 \
  --query "Stacks[0].Outputs[?OutputKey=='FrontendBucketName'].OutputValue" \
  --output text)

aws s3 sync dist/ "s3://$BUCKET/" --delete
```

Invalidate the CloudFront cache so the new files are served immediately:

```bash
DIST_ID=$(aws cloudformation describe-stacks \
  --stack-name christmas-tree-store \
  --region us-east-1 \
  --query "Stacks[0].Outputs[?OutputKey=='CloudFrontUrl'].OutputValue" \
  --output text | sed 's|https://||' | cut -d'.' -f1)

# Get the actual distribution ID
DIST_ID=$(aws cloudfront list-distributions \
  --query "DistributionList.Items[?contains(DomainName, '$DIST_ID')].Id" \
  --output text)

aws cloudfront create-invalidation \
  --distribution-id "$DIST_ID" \
  --paths "/*"
```

> **Simpler alternative:** Go to AWS Console → CloudFront → your distribution → Invalidations → Create, path `/*`.

### 2.9 Verify the live deployment

```bash
CF_URL=$(aws cloudformation describe-stacks \
  --stack-name christmas-tree-store \
  --region us-east-1 \
  --query "Stacks[0].Outputs[?OutputKey=='CloudFrontUrl'].OutputValue" \
  --output text)

# SPA loads
curl -s -o /dev/null -w "%{http_code}" "$CF_URL/"
# Expected: 200

# Health check via CloudFront → API Gateway
curl -s "$CF_URL/api/health"
# Expected: {"status":"ok","service":"christmas-tree-store"}

# Products endpoint
curl -s "$CF_URL/api/products" | python3 -m json.tool | head -20
# Expected: {"products":[...]}
```

Open `$CF_URL` in your browser. You should see the live Christmas tree catalog over HTTPS.

### 2.10 Place a live test order

1. Open the CloudFront URL in a browser.
2. Click **Shop**, select a tree.
3. Click **Order Now** — you will be redirected to `/auth`.
4. Click **Create account**, enter a real email address, and sign up.
5. Check that email for the verification code; enter it in the **Confirm account** form.
6. Sign in and fill out the order form.
7. Submit — you should reach the confirmation page with an `orderId`.
8. If you set a `RetailerEmail` in step 2.3, check that inbox for the retailer notification email.

Verify the order in DynamoDB:

```bash
aws dynamodb scan \
  --table-name christmas-tree-store-orders \
  --region us-east-1 \
  --no-cli-pager
```

---

## Part 3 — Teardown (AWS)

> This deletes all AWS resources created by the stack, including S3, DynamoDB, Cognito, and CloudFront.

Empty the S3 bucket first (CloudFormation cannot delete a non-empty bucket):

```bash
BUCKET=$(aws cloudformation describe-stacks \
  --stack-name christmas-tree-store \
  --region us-east-1 \
  --query "Stacks[0].Outputs[?OutputKey=='FrontendBucketName'].OutputValue" \
  --output text)

aws s3 rm "s3://$BUCKET/" --recursive
```

Delete the stack:

```bash
sam delete --stack-name christmas-tree-store --region us-east-1
```

Confirm when prompted. The stack deletion takes ~2–3 minutes.

---

## Troubleshooting

### `sam local start-api` fails with "image not found"
SAM needs Docker running. Start Docker Desktop or the Docker daemon, then retry.

### `curl http://localhost:3000/products` returns 403
Check `local-env.json` — `PRODUCTS_TABLE` must match the DynamoDB Local table name (`christmas-tree-store-products`). Also ensure DynamoDB Local is running (`docker compose ps`).

### CloudFormation deploy fails on `FrontendBucketPolicy`
The bucket policy references the CloudFront distribution ARN. This is a known timing issue — simply re-run `sam deploy`. CloudFormation retry usually resolves it.

### SNS email notification not received
Ensure you clicked the subscription confirmation link in the AWS email. Check the SNS Console → Subscriptions — status must be `Confirmed`, not `PendingConfirmation`.

### Frontend shows "Network Error" in browser
The `VITE_API_URL` in `.env.production.local` must not have a trailing slash and must match the CloudFront URL exactly. Rebuild and re-sync after any change.

### DynamoDB Local tables already exist error
Re-running `setup-local.sh` is safe — the script ignores "Table already exists" errors.
