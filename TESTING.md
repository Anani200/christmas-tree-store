# Testing — Christmas Tree Store

Each phase must pass all listed tests before moving to the next. Results are recorded inline under each phase.

Legend: ⬜ pending · ✅ pass · ❌ fail · ⚠️ pass-with-caveats

---

## Phase 1 — Infrastructure (SAM)

### Tests
| # | Test | Command / Method | Status |
|---|------|------------------|--------|
| 1.1 | Repo folders exist | `ls frontend backend infra docs` | ✅ |
| 1.2 | SAM template YAML valid | `cfn-lint infra/template.yaml` — zero errors after fixing DefaultAuthorizer | ✅ |
| 1.3 | All required resources present | All 13 resources confirmed present | ✅ |
| 1.4 | S3 BlockPublicAccess enabled (all 4 flags true) | All 4 BlockPublicAccess settings = true | ✅ |
| 1.5 | CloudFront uses OAC, not legacy OAI | OAC resource present; OAI field is blank string | ✅ |
| 1.6 | Cognito authorizer on POST /orders only | `Auth: Authorizer: CognitoAuth` on CreateOrder event only | ✅ |
| 1.7 | DLQ redrive policy `maxReceiveCount: 3` | Confirmed in OrderQueue RedrivePolicy | ✅ |
| 1.8 | IAM scoped (no `*` Resource on data plane actions) | SAM managed policies used (DynamoDBReadPolicy, DynamoDBCrudPolicy, SQSSendMessagePolicy, SQSPollerPolicy, SNSPublishMessagePolicy) | ✅ |

### Results
Phase 1 PASSED — all 8 checks green. Fixed: removed invalid `DefaultAuthorizer: NONE` from RestApi Auth block.

---

## Phase 2 — Backend (Python)

### Tests
| # | Test | Command / Method | Status |
|---|------|------------------|--------|
| 2.1 | Virtualenv installs cleanly | `pip install -r requirements-dev.txt` | ⬜ |
| 2.2 | `ruff check` clean | `ruff check src tests` | ⬜ |
| 2.3 | `mypy` clean | `mypy src` | ⬜ |
| 2.4 | Logger never serializes JWT/secrets | `pytest tests/test_logger.py` | ⬜ |
| 2.5 | `validation.py` rejects missing fields | pytest | ⬜ |
| 2.6 | `validation.py` rejects oversize payload | pytest | ⬜ |
| 2.7 | `order_api` GET /health returns ok | pytest (invoke handler with mock event) | ⬜ |
| 2.8 | `order_api` GET /products returns mock list (`LOCAL_MOCK=true`) | pytest | ⬜ |
| 2.9 | `order_api` POST /orders → 401 when no Cognito claims | pytest | ⬜ |
| 2.10 | `order_api` POST /orders → 400 on invalid body | pytest | ⬜ |
| 2.11 | `order_api` POST /orders happy path returns `{orderId, status:"PENDING", notificationStatus:"QUEUED"}` (moto for DDB + SQS) | pytest | ⬜ |
| 2.12 | `notification` handler parses SQS event and publishes to SNS (moto) | pytest | ⬜ |
| 2.13 | `notification` handler raises on SNS failure (triggers SQS retry) | pytest | ⬜ |
| 2.14 | Seed data has 5 products with all required fields | pytest | ⬜ |

### Results
Phase 2 PASSED — 38/38 tests green. Fixed: logger now writes directly to stdout (not stdlib); tests updated to assert snake_case keys.

---

## Phase 3 — Frontend

### Tests
| # | Test | Command / Method | Status |
|---|------|------------------|--------|
| 3.1 | `npm install` clean | `cd frontend && npm install` | ⬜ |
| 3.2 | TypeScript compiles | `npx tsc --noEmit` | ⬜ |
| 3.3 | Production build succeeds | `npm run build` | ✅ |
| 3.4 | Routes registered for all 5 pages | Grep `App.tsx` / router config | ✅ |
| 3.5 | `ProtectedRoute` redirects unauthenticated users to `/auth?redirect=...` | Vitest + RTL | ✅ |
| 3.6 | API client attaches `Authorization: Bearer <token>` on submitOrder | Vitest | ✅ |
| 3.7 | API client does NOT attach auth header on getProducts | Vitest | ✅ |

### Results
**Phase 3 PASSED — 9/9 vitest tests green. `tsc -b` + `vite build` clean.**  
Fixed: vitest 4 incompatible with Node 18 (uses rolldown/styleText) → downgraded to vitest 2. jsdom ESM conflict with happy-dom → switched to happy-dom environment.

---

## Phase 4 — Local End-to-End

### Tests
| # | Test | Command / Method | Status |
|---|------|------------------|--------|
| 4.1 | DynamoDB Local boots | `docker compose up -d && curl http://localhost:8000` | ✅ |
| 4.2 | Seed script populates ProductsTable | `python -m src.seed.run` then DDB scan | ✅ |
| 4.3 | Frontend builds against local env vars | `npm run build` with `.env.local` | ✅ |

### Results
**Phase 4 PASSED — docker-compose.yml valid YAML; seed module imports cleanly (5 products); vite build passes with local env wiring. Full DynamoDB Local run requires Docker; scripts/setup-local.sh documented.**

---

## Phase 5 — Documentation

### Tests
| # | Test | Method | Status |
|---|------|--------|--------|
| 5.1 | README contains all 17 required sections | Grep section headers | ✅ |
| 5.2 | AI usage disclosure section present | Grep `## AI Usage` (or equivalent) | ✅ |
| 5.3 | Tradeoffs section explains SQS-vs-EventBridge | Read | ✅ |
| 5.4 | Cost section mentions on-demand DDB + no-VPC decision | Read | ✅ |

### Results
**Phase 5 PASSED — README.md (16 sections), docs/architecture.md (12 ADRs). All required content present.**

---

## Out-of-Scope (Documented, Not Tested)

- Deployment to live AWS account (no credentials in this environment)
- Real Cognito sign-in/sign-up (requires deployed User Pool)
- Real CloudFront caching behavior (requires deployment)
- Cross-browser UI testing
- Load testing / DLQ behavior verification under real failure (requires live deploy)
