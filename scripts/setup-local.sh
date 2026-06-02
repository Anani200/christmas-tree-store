#!/usr/bin/env bash
# scripts/setup-local.sh
# Creates DynamoDB Local tables and seeds product data.
# Requires DynamoDB Local running on port 8000 (see docker-compose.yml).
set -euo pipefail

ENDPOINT="http://localhost:8000"
PRODUCTS_TABLE="christmas-tree-store-products"
ORDERS_TABLE="christmas-tree-store-orders"

echo "==> Creating ProductsTable..."
aws dynamodb create-table \
  --endpoint-url "$ENDPOINT" \
  --table-name "$PRODUCTS_TABLE" \
  --attribute-definitions AttributeName=productId,AttributeType=S \
  --key-schema AttributeName=productId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1 \
  --no-cli-pager 2>&1 | grep -E "TableName|TableStatus" || true

echo "==> Creating OrdersTable..."
aws dynamodb create-table \
  --endpoint-url "$ENDPOINT" \
  --table-name "$ORDERS_TABLE" \
  --attribute-definitions AttributeName=orderId,AttributeType=S \
  --key-schema AttributeName=orderId,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1 \
  --no-cli-pager 2>&1 | grep -E "TableName|TableStatus" || true

echo "==> Seeding product data..."
cd backend
DDB_ENDPOINT="$ENDPOINT" PRODUCTS_TABLE="$PRODUCTS_TABLE" \
  .venv/bin/python -m src.seed.run

echo ""
echo "✓ Local setup complete."
echo "  Start API: cd backend && LOCAL_MOCK=false PRODUCTS_TABLE=$PRODUCTS_TABLE ORDERS_TABLE=$ORDERS_TABLE DDB_ENDPOINT=$ENDPOINT sam local start-api -t ../infra/template.yaml"
