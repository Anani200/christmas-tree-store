"""Seed script — writes all product records to DynamoDB.

Usage (local DynamoDB):
    DDB_ENDPOINT=http://localhost:8000 PRODUCTS_TABLE=christmas-tree-store-products \
        python -m src.seed.run

Usage (real AWS):
    PRODUCTS_TABLE=christmas-tree-store-products python -m src.seed.run
"""
from __future__ import annotations

import os
import sys

import boto3

from src.seed.products import PRODUCTS


def main() -> None:
    table_name = os.environ.get("PRODUCTS_TABLE", "christmas-tree-store-products")
    endpoint = os.environ.get("DDB_ENDPOINT")

    kwargs: dict = {"region_name": os.environ.get("AWS_DEFAULT_REGION", "us-east-1")}
    if endpoint:
        kwargs["endpoint_url"] = endpoint

    dynamodb = boto3.resource("dynamodb", **kwargs)
    table = dynamodb.Table(table_name)

    print(f"Seeding {len(PRODUCTS)} products into '{table_name}'...")
    with table.batch_writer() as batch:
        for product in PRODUCTS:
            batch.put_item(Item=product)

    print("Done. Products seeded successfully.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
