# Christmas Tree Store — Architecture & Engineering Presentation

> **Seasonal serverless ecommerce on AWS**  
> A production-grade system designed for near-zero cost at rest and elastic scale during peak season.

---

## 1. Problem Statement

A local Christmas tree retailer needs an online presence to accept pre-orders for tree pickup during the November–December season. The system must:

- Serve a product catalog to unauthenticated visitors
- Allow customers to create accounts and place orders
- Notify the retailer by email for every new order
- Cost almost nothing during the 10 months of off-season
- Require no operational overhead (no servers to patch or scale)

---

## 2. Architecture Overview

```
Browser
  │
  ├─ HTTPS ──► CloudFront
  │                 │
  │         ┌───────┴────────────────────┐
  │         │                            │
  │       S3 Bucket               API Gateway (Regional REST)
  │     (React SPA)                      │
  │                        ┌────────────┬┴────────────┐
  │                        │            │             │
  │                  GET /health   GET /products   POST /orders
  │                  GET /products/{id}             │
  │                        │                        │
  │                  OrderApiFunction          ──► DynamoDB OrdersTable
  │                  (Lambda, Python 3.12)     ──► SQS OrderQueue
  │                                                  │
  │                                            NotificationFunction
  │                                            (Lambda, SQS trigger)
  │                                                  │
  │                                             SNS Topic ──► Email
  │
  └─ POST /auth/* ──► AuthFunction (Lambda)
                           │
                      Cognito User Pool (USER_PASSWORD_AUTH)
```

Two Lambda functions handle all compute:
- **OrderApiFunction** — product catalog + order creation (REST)
- **AuthFunction** — Cognito proxy for register/login/confirm/refresh/logout
- **NotificationFunction** — SQS-triggered email dispatch via SNS

---

## 3. Architectural Decisions

### 3.1 Serverless-First (Lambda + API Gateway)

**Decision:** All compute runs on Lambda; no EC2, ECS, or containers.

**Reasoning:**
- Seasonal traffic profile: near-zero for 10 months, sharp spike in November–December. A traditional server would sit idle 83% of the year and still incur ~$30–$50/month minimum.
- Lambda billing is per-invocation ($0.0000002 per request). At 500 orders/season the compute cost is unmeasurably small.
- No patching, no AMI management, no autoscaling groups.
- Cold starts are acceptable for a pickup-order flow (no real-time SLA).

**Tradeoff accepted:** No persistent connections (e.g., no WebSockets). This is acceptable because the store is a request/response catalog + form submission, not a real-time application.

---

### 3.2 API Gateway REST (not HTTP API v2)

**Decision:** Regional REST API rather than the newer, cheaper HTTP API.

**Reasoning:**
- REST API supports native Cognito User Pool authorizer on individual routes (`POST /orders`). No custom Lambda authorizer code is needed.
- HTTP API v2 is ~70% cheaper per request but requires a custom Lambda authorizer to validate Cognito JWTs — extra code surface, extra Lambda cold start, extra IAM role.
- For 500 orders/season the price difference is fractions of a cent. The simplicity of the native authorizer is worth it.

**Tradeoff accepted:** Higher per-request cost than HTTP API v2 (negligible at this scale).

---

### 3.3 CloudFront in Front of API Gateway

**Decision:** API Gateway is Regional (not Edge-optimized); CloudFront sits in front of both the SPA and the API (`/api/*` behaviour).

**Reasoning:**
- A single CloudFront distribution unifies the SPA and the API under one domain (no CORS issues in production).
- The SPA's static assets are cached at edge globally. API calls are forwarded to a single Regional endpoint, which is optimal for domestic seasonal traffic.
- Edge-optimized API Gateway costs more and duplicates what CloudFront already provides.
- OAC on the S3 origin means S3 never has public access, regardless of future bucket policy mistakes.

---

### 3.4 DynamoDB On-Demand

**Decision:** Both tables use `BillingMode: PAY_PER_REQUEST` with no provisioned capacity.

**Reasoning:**
- Traffic is unpredictable and bursty. Provisioned capacity would require a capacity estimate that is almost certainly wrong for a seasonal store.
- On-demand pricing scales to zero between seasons.
- At 500 orders and ~5,000 product reads per season the DynamoDB cost is under $0.01.
- Point-in-time recovery (PITR) enabled on both tables at no extra cost (covered by standard pricing).

**Tradeoff accepted:** On-demand has higher per-read cost than provisioned with reservations. This is irrelevant at this scale.

---

### 3.5 Cognito Auth Proxy Pattern (No Amplify SDK in Browser)

**Decision:** All Cognito calls go through a Lambda (`AuthFunction`) rather than directly from the browser using the Amplify SDK or AWS SDK.

**Reasoning:**
- The Amplify SDK would expose `USER_POOL_ID` and `USER_POOL_CLIENT_ID` in the browser bundle. While these values are not secret, calling Cognito directly from the browser locks the frontend to Cognito's specific API shape — swapping auth providers later would require a frontend rewrite.
- The Lambda proxy pattern means the frontend calls `POST /api/auth/login` with email/password and receives tokens. It never knows or cares that Cognito is the backend.
- The auth Lambda itself never handles raw passwords or tokens in logs — it only passes them through to Cognito over TLS.
- Tokens are stored in `sessionStorage` (not `localStorage`) so they are cleared when the browser tab closes, reducing the window of exposure.

**Tradeoff accepted:** One extra Lambda hop per auth call (~10–30ms latency). Acceptable for an authentication flow.

---

### 3.6 SQS → Lambda → SNS Decoupled Notifications

**Decision:** Order confirmation emails go through SQS → Lambda → SNS rather than calling SNS directly from the order Lambda.

**Reasoning:**
- Order creation and notification are independent concerns. If SNS is temporarily unavailable, the order should still succeed and be saved.
- SQS provides a durable buffer with configurable retry: `maxReceiveCount: 3` before the message goes to the Dead Letter Queue.
- The `NotificationFunction` is independently scalable — email throughput is decoupled from API response time.
- The DLQ gives the retailer a safety net: failed notifications are inspectable and replayable from the AWS Console without data loss.

**Tradeoff accepted:** Retailer email arrives asynchronously (typically within 1–5 seconds). This is fine for a pickup-order workflow.

---

### 3.7 arm64 / Graviton2 for All Lambdas

**Decision:** `Architectures: [arm64]` in the SAM globals.

**Reasoning:**
- Graviton2 Lambda is ~20% cheaper per GB-second than x86 and typically 10–19% faster for Python workloads.
- Python 3.12 runtime is fully supported on arm64.
- boto3 and all dependencies are platform-independent pure-Python wheels — no recompilation needed.
- Zero code changes required; the switch is a single YAML line.

---

### 3.8 S3 + CloudFront with Origin Access Control (OAC)

**Decision:** Frontend is a React SPA deployed to S3, served via CloudFront with OAC. S3 public access is fully blocked.

**Reasoning:**
- OAC is the AWS-recommended successor to OAI (Origin Access Identity) and supports all S3 API operations including SSE-KMS.
- No public S3 URL is ever exposed, preventing direct access that bypasses CloudFront (and its WAF/logging).
- Vite builds a fully static bundle — no server-side rendering needed, which would require Lambda@Edge or a container.

---

### 3.9 Single Lambda for All REST Routes

**Decision:** One `OrderApiFunction` handles all product and order routes rather than a Lambda per route.

**Reasoning:**
- Five routes in a single small team does not justify the operational overhead of five separate functions, five IAM roles, and five CloudWatch log groups.
- A single Lambda shares one connection pool to DynamoDB and one SQS client, reducing per-invocation initialization cost.
- The internal router (`_ROUTES` dict) is trivial and adds no meaningful complexity.

**Tradeoff accepted:** All routes share a single cold-start. Independent scaling per route is not possible. Both are acceptable given the scale.

---

### 3.10 No VPC

**Decision:** Lambdas run outside a VPC (default network).

**Reasoning:**
- DynamoDB, SQS, SNS, and Cognito are AWS public endpoints accessible from Lambda's default network without a NAT Gateway.
- A VPC + private subnets + NAT Gateway adds ~$32–$45/month minimum (NAT Gateway hourly charge). This would be the largest single cost item in the system.
- VPC also adds 1–10 second cold starts when ENI attachment is required.
- There are no private resources (no RDS, no self-managed Redis) that would require VPC membership.

---

## 4. Implementation Approach

### 4.1 Infrastructure as Code — AWS SAM

The entire stack is defined in a single `infra/template.yaml` SAM template. This includes:

- DynamoDB tables (products, orders)
- Lambda functions with IAM policies scoped to specific resource ARNs
- API Gateway with Cognito authorizer and CORS configuration
- SQS queue + DLQ with `maxReceiveCount: 3`
- SNS topic with optional email subscription
- CloudFront distribution with two origins (S3 and API Gateway)
- S3 bucket with OAC and all `BlockPublicAccess` flags

A single `sam deploy` command creates or updates all 20+ resources as one atomic CloudFormation stack.

### 4.2 Backend — Python 3.12

**Structure:**
```
backend/src/
├── handlers/
│   ├── order_api.py     # REST routes: health, products, orders
│   ├── auth.py          # Auth proxy: login, register, confirm, refresh, logout
│   └── notification.py  # SQS trigger: SNS email dispatch
├── seed/
│   ├── products.py      # 5 product records (seed data)
│   └── run.py           # One-shot DynamoDB seeder script
└── utils/
    ├── logger.py        # Structured JSON logger with sensitive key redaction
    ├── response.py      # HTTP response builders (ok, bad_request, not_found, error)
    └── validation.py    # Order request validation
```

**Key patterns:**
- **Lazy AWS client initialisation**: clients are created once per Lambda container (module-level singletons), not per request. This avoids redundant TLS handshakes on warm invocations.
- **botocore standard retry mode**: `Config(retries={"max_attempts": 3, "mode": "standard"})` on every boto3 client. Standard mode uses exponential backoff with jitter on throttling and transient errors.
- **DynamoDB pagination**: `_list_products` uses a `LastEvaluatedKey` loop to handle tables larger than 1 MB (DynamoDB's single `scan` page limit).
- **Server-side product resolution**: `_create_order` fetches the product from DynamoDB and uses its `name` field. The client only supplies `productId` — this prevents a malicious client from injecting a false `productName` into the order record.
- **`LOCAL_MOCK=true` test mode**: All AWS calls are gated behind an environment variable check. Unit tests run against in-memory seed data with no AWS credentials required.

### 4.3 Frontend — React + TypeScript + Vite

**Structure:**
```
frontend/src/
├── api/client.ts         # HTTP client with timeout + retry
├── context/AuthContext.tsx # Auth state, token storage, Cognito proxy calls
├── components/           # Reusable UI: Navbar, TreeCard, TreeImage, Snow
├── pages/                # Route-level pages: Catalog, ProductDetail, OrderForm, Auth
└── config/               # (empty — AWS config removed; auth goes through Lambda proxy)
```

**Key patterns:**
- **No AWS SDK in browser**: plain `fetch` calls to `/api/*`. Zero AWS dependency in the frontend bundle.
- **`fetchWithTimeout`**: every request carries an `AbortController` with a 10-second deadline. This prevents requests from hanging indefinitely if API Gateway or Lambda is unresponsive.
- **`fetchWithRetry` (GET only)**: product catalog and detail requests retry up to 3 times with exponential backoff (~100/200/400 ms + jitter) on HTTP 429, 500, 502, 503, 504. POST /orders is not retried — non-idempotent requests must not be duplicated.
- **`sessionStorage` for tokens**: ID token, access token, and refresh token are stored in `sessionStorage`. Cleared automatically when the browser tab or window closes.
- **Automatic token refresh**: `AuthContext` checks token expiry 60 seconds before it occurs and calls `POST /api/auth/refresh` transparently.

### 4.4 Testing Strategy

**Backend (pytest, 52 tests):**
- All tests run with `LOCAL_MOCK=true` — no AWS calls, no mocking library (no `moto`, no `unittest.mock`)
- Tests cover: happy path, validation failures, auth edge cases (expired tokens, unconfirmed accounts), notification error propagation
- Logger tests validate structured JSON output and sensitive key redaction

**Frontend (Vitest + React Testing Library):**
- API client timeout/retry behaviour tested with `vi.useFakeTimers()`
- `ProtectedRoute` redirect logic tested against both authenticated and unauthenticated context states

---

## 5. Engineering Reasoning Summary

| Decision | Core Reason |
|----------|-------------|
| Serverless Lambda | Zero cost at rest; scales automatically during peak season |
| REST API Gateway | Native Cognito authorizer — no custom auth code required |
| CloudFront unified domain | One HTTPS endpoint; no CORS in production |
| DynamoDB on-demand | Pay-per-request; scales to zero off-season |
| Auth Lambda proxy | Frontend never calls Cognito directly; provider-agnostic |
| SQS decoupled notifications | Order creation never blocked by email failures |
| arm64 Graviton2 | 20% cheaper per GB-second; zero code changes needed |
| OAC (not OAI) | Current AWS best practice; prevents direct S3 access |
| No VPC | Saves ~$40/month on NAT Gateway; no private resources exist |
| Single OrderApiFunction | Five routes in one small Lambda; simpler ops at this scale |
| botocore standard retry | Automatic exponential backoff on AWS throttling/transient errors |
| Paginated DynamoDB scan | Handles catalogs > 1 MB without silently truncating results |
| Server-side product lookup | Prevents `productName` injection from a malicious client |
| `sessionStorage` for tokens | Tokens cleared on tab close; shorter exposure window than `localStorage` |
| `LOCAL_MOCK=true` test mode | Full test suite runs with no AWS credentials; fast and deterministic |

---

## 6. Cost Model

| Scenario | Estimated Monthly Cost |
|----------|----------------------|
| Off-season (Jan–Oct) — near-zero traffic | **< $0.02** (CloudFront minimum) |
| Peak season (Nov–Dec) — ~500 orders/month | **< $0.15** |
| DynamoDB provisioned + NAT Gateway alternative | **~$45+/month** |

The serverless architecture saves approximately **$540/year** compared to a minimal always-on EC2 + RDS setup, while requiring less operational work.

---

## 7. Security Posture

| Layer | Control |
|-------|---------|
| Transport | HTTPS enforced by CloudFront (HTTP → HTTPS redirect) |
| S3 | All `BlockPublicAccess` flags set; only CloudFront OAC reads the bucket |
| Auth | Cognito JWTs validated by API Gateway; Lambda only receives verified claims |
| Token storage | `sessionStorage` only — cleared on tab close |
| Input validation | Server-side required fields, max lengths, email format, date format |
| Product injection | `productName` resolved server-side from DynamoDB, not from client input |
| IAM | All Lambda policies scoped to specific DynamoDB table, SQS queue, SNS topic ARNs |
| CORS | Explicit origin allowlist; no `*` wildcard; `CorsAllowedOrigin` parameter |
| Logging | Sensitive fields (`token`, `password`, `authorization`) auto-redacted before CloudWatch |
| SQS reliability | DLQ captures messages after 3 failed delivery attempts |

---

## 8. Scalability Path

The current design handles the stated requirements comfortably. If the business grows:

1. **Multiple tree varieties / high catalog volume** — DynamoDB scan replaced with a GSI-based query or ElasticSearch integration
2. **Inventory management** — DynamoDB `UpdateItem` with `ConditionExpression` for atomic stock decrement
3. **Multi-region** — DynamoDB Global Tables + CloudFront multi-origin (no Lambda code changes)
4. **Admin portal** — Separate Cognito group (`admin`), new Lambda authorizer checking group membership, React admin route behind `ProtectedRoute`
5. **Payment processing** — Stripe Checkout session created before `POST /orders`; order Lambda becomes idempotent via `ConditionExpression` on `orderId`
6. **CI/CD** — GitHub Actions: `ruff` + `mypy` + `pytest` → `sam build` → `sam deploy` → `aws s3 sync`
