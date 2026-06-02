#!/usr/bin/env bash
# scripts/setup-aws.sh
#
# Full AWS deployment for the Christmas Tree Store.
# Usage:
#   ./scripts/setup-aws.sh                          # deploy with no retailer email
#   RETAILER_EMAIL=you@example.com ./scripts/setup-aws.sh
#   STACK_NAME=my-stack REGION=eu-west-1 ./scripts/setup-aws.sh
#
# Environment variables (all optional):
#   STACK_NAME       CloudFormation stack name   (default: christmas-tree-store)
#   REGION           AWS region                  (default: us-east-1)
#   RETAILER_EMAIL   SNS notification email      (default: empty — no email)
#   PROJECT_NAME     Resource name prefix        (default: christmas-tree-store)
#
# Requires: aws-cli v2, sam-cli 1.120+, python3.12, node 18+

set -euo pipefail

# ─── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
step()  { echo -e "\n${CYAN}==> $*${NC}"; }
ok()    { echo -e "${GREEN}    ✓ $*${NC}"; }
warn()  { echo -e "${YELLOW}    ⚠ $*${NC}"; }
die()   { echo -e "${RED}    ✗ $*${NC}" >&2; exit 1; }

# ─── Config ───────────────────────────────────────────────────────────────────
STACK_NAME="${STACK_NAME:-christmas-tree-store}"
REGION="${REGION:-us-east-1}"
PROJECT_NAME="${PROJECT_NAME:-christmas-tree-store}"
RETAILER_EMAIL="${RETAILER_EMAIL:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ─── 1. Prerequisites ─────────────────────────────────────────────────────────
step "Checking prerequisites"

command -v aws  >/dev/null 2>&1 || die "aws CLI not found — install from https://aws.amazon.com/cli/"
command -v sam  >/dev/null 2>&1 || die "sam CLI not found — install from https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html"
command -v node >/dev/null 2>&1 || die "node not found — install Node.js 18+"
command -v npm  >/dev/null 2>&1 || die "npm not found"

# Python 3.12 specifically
PYTHON=""
for py in python3.12 python3 python; do
  if command -v "$py" >/dev/null 2>&1 && $py --version 2>&1 | grep -q "3\.12"; then
    PYTHON="$py"; break
  fi
done
[[ -z "$PYTHON" ]] && die "Python 3.12 not found — required for Lambda runtime parity"

ok "aws $(aws --version 2>&1 | awk '{print $1}')"
ok "sam $(sam --version)"
ok "node $(node --version)"
PYTHON_VER=$($PYTHON --version 2>&1); ok "$PYTHON ($PYTHON_VER)"

# ─── 2. AWS credentials ───────────────────────────────────────────────────────
step "Verifying AWS credentials (region: $REGION)"
CALLER_IDENTITY=$(aws sts get-caller-identity --region "$REGION" --output json 2>&1) \
  || die "AWS credentials not configured — run: aws configure"
ACCOUNT_ID=$(echo "$CALLER_IDENTITY" | python3 -c "import sys,json; print(json.load(sys.stdin)['Account'])")
ok "Account: $ACCOUNT_ID"

# ─── 3. SAM build ─────────────────────────────────────────────────────────────
step "Building SAM application"
cd "$ROOT/infra"
sam build
ok "SAM build complete"

# ─── 4. SAM deploy ────────────────────────────────────────────────────────────
step "Deploying CloudFormation stack: $STACK_NAME"

PARAM_OVERRIDES="ProjectName=$PROJECT_NAME CorsAllowedOrigin=http://localhost:5173"
if [[ -n "$RETAILER_EMAIL" ]]; then
  PARAM_OVERRIDES="$PARAM_OVERRIDES RetailerEmail=$RETAILER_EMAIL"
  warn "SNS email set — check inbox for subscription confirmation after deploy"
fi

sam deploy \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --capabilities CAPABILITY_IAM \
  --resolve-s3 \
  --no-confirm-changeset \
  --no-fail-on-empty-changeset \
  --parameter-overrides $PARAM_OVERRIDES

ok "Stack deployed"

# ─── 5. Fetch stack outputs ───────────────────────────────────────────────────
step "Fetching stack outputs"

get_output() {
  aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" \
    --output text
}

CF_URL=$(get_output "CloudFrontUrl")
BUCKET=$(get_output "FrontendBucketName")
DIST_ID=$(aws cloudfront list-distributions \
  --query "DistributionList.Items[?DomainName=='${CF_URL#https://}'].Id" \
  --output text 2>/dev/null || true)
# Fallback: find distribution ID via stack resource
if [[ -z "$DIST_ID" ]]; then
  DIST_ID=$(aws cloudformation describe-stack-resources \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query "StackResources[?ResourceType=='AWS::CloudFront::Distribution'].PhysicalResourceId" \
    --output text)
fi
USER_POOL_ID=$(get_output "UserPoolId")
USER_POOL_CLIENT_ID=$(get_output "UserPoolClientId")

ok "CloudFront URL:   $CF_URL"
ok "S3 Bucket:        $BUCKET"
ok "Distribution ID:  $DIST_ID"
ok "User Pool ID:     $USER_POOL_ID"
ok "Client ID:        $USER_POOL_CLIENT_ID"

# ─── 6. Seed DynamoDB ─────────────────────────────────────────────────────────
step "Seeding product catalog"
cd "$ROOT/backend"

if [[ ! -d ".venv" ]]; then
  "$PYTHON" -m venv .venv
fi
.venv/bin/pip install -q -r requirements.txt

PRODUCTS_TABLE="$PROJECT_NAME-products" \
AWS_DEFAULT_REGION="$REGION" \
  .venv/bin/python -m src.seed.run

COUNT=$(aws dynamodb scan \
  --table-name "$PROJECT_NAME-products" \
  --region "$REGION" \
  --query "Count" \
  --output text \
  --no-cli-pager)
ok "$COUNT products seeded"

# ─── 7. Build frontend ────────────────────────────────────────────────────────
step "Building frontend"
cd "$ROOT/frontend"

cat > .env.production.local << EOF
VITE_API_URL=$CF_URL
VITE_USER_POOL_ID=$USER_POOL_ID
VITE_USER_POOL_CLIENT_ID=$USER_POOL_CLIENT_ID
VITE_REGION=$REGION
EOF
ok "Written .env.production.local"

npm install --silent
npm run build
ok "Frontend built (dist/)"

# ─── 8. Deploy frontend to S3 ─────────────────────────────────────────────────
step "Uploading frontend to S3"
aws s3 sync dist/ "s3://$BUCKET/" --delete --quiet
ok "Uploaded to s3://$BUCKET/"

# ─── 9. Update CORS to CloudFront URL ─────────────────────────────────────────
step "Updating CORS allowed origin to $CF_URL"
cd "$ROOT/infra"

sam deploy \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --capabilities CAPABILITY_IAM \
  --resolve-s3 \
  --no-confirm-changeset \
  --no-fail-on-empty-changeset \
  --parameter-overrides "ProjectName=$PROJECT_NAME CorsAllowedOrigin=$CF_URL ${RETAILER_EMAIL:+RetailerEmail=$RETAILER_EMAIL}" \
  --quiet 2>/dev/null || \
sam deploy \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --capabilities CAPABILITY_IAM \
  --resolve-s3 \
  --no-confirm-changeset \
  --no-fail-on-empty-changeset \
  --parameter-overrides "ProjectName=$PROJECT_NAME CorsAllowedOrigin=$CF_URL"

ok "CORS updated"

# ─── 10. CloudFront cache invalidation ────────────────────────────────────────
step "Invalidating CloudFront cache"
aws cloudfront create-invalidation \
  --distribution-id "$DIST_ID" \
  --paths "/*" \
  --query "Invalidation.Id" \
  --output text \
  --no-cli-pager
ok "Invalidation created"

# ─── 11. Smoke test ───────────────────────────────────────────────────────────
step "Running smoke tests"
echo "    Waiting 10 s for propagation..."
sleep 10

SPA_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$CF_URL/")
HEALTH_BODY=$(curl -s "$CF_URL/api/health")
PRODUCTS_COUNT=$(curl -s "$CF_URL/api/products" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('products',[])))" 2>/dev/null || echo "?")

[[ "$SPA_STATUS" == "200" ]] && ok "SPA:      HTTP $SPA_STATUS" || die "SPA returned HTTP $SPA_STATUS"
echo "$HEALTH_BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('status')=='ok'" 2>/dev/null \
  && ok "Health:   $HEALTH_BODY" || die "Health check failed: $HEALTH_BODY"
[[ "$PRODUCTS_COUNT" == "5" ]] && ok "Products: $PRODUCTS_COUNT found" || warn "Products: expected 5, got $PRODUCTS_COUNT"

# ─── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Deployment complete!                                ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║  Live URL:  $CF_URL${NC}"
echo -e "${GREEN}║  Stack:     $STACK_NAME ($REGION)${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
if [[ -n "$RETAILER_EMAIL" ]]; then
  warn "Action required: confirm the SNS subscription email sent to $RETAILER_EMAIL"
fi
