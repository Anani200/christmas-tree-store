"""Notification Lambda handler.

Triggered by SQS OrderQueue (batch size 1).
Reads each ORDER_CREATED message and publishes a human-readable
notification to the SNS OrderNotificationsTopic.

On any failure the exception is re-raised so SQS will retry the message.
After maxReceiveCount retries the message moves to the DLQ.

Environment variables:
  SNS_TOPIC_ARN   — ARN of the OrderNotificationsTopic
  LOCAL_MOCK      — set to "true" to skip AWS calls (unit tests)
"""
from __future__ import annotations

import json
import os
from typing import Any

import boto3
from botocore.config import Config

from src.utils.logger import get_logger

log = get_logger("order-notification")

_BOTO_CONFIG = Config(retries={"max_attempts": 3, "mode": "standard"})

_sns = None


def _get_sns():
    global _sns
    if _sns is None:
        _sns = boto3.client(
            "sns",
            region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
            config=_BOTO_CONFIG,
        )
    return _sns


def _build_notification(order: dict) -> tuple[str, str]:
    """Return (subject, message) for the SNS notification."""
    subject = "New Christmas Tree Order Received"
    message = (
        f"New order received.\n\n"
        f"Order ID:              {order.get('orderId', 'N/A')}\n"
        f"Customer:              {order.get('customerName', 'N/A')}\n"
        f"Email:                 {order.get('customerEmail', 'N/A')}\n"
        f"Phone:                 {order.get('customerPhone', 'N/A')}\n"
        f"Product:               {order.get('productName', 'N/A')}\n"
        f"Quantity:              {order.get('quantity', 'N/A')}\n"
        f"Preferred Pickup Date: {order.get('preferredPickupDate', 'N/A')}\n"
        f"Status:                {order.get('status', 'N/A')}\n"
    )
    return subject, message


def _process_record(record: dict) -> None:
    body_raw = record.get("body", "{}")
    log.info("sqs_message_received", message_id=record.get("messageId", "unknown"))

    try:
        order = json.loads(body_raw)
    except json.JSONDecodeError as exc:
        log.error("sqs_message_parse_error", error=str(exc))
        raise

    order_id = order.get("orderId", "unknown")
    log.info("order_notification_processing", order_id=order_id)

    subject, message = _build_notification(order)

    if os.environ.get("LOCAL_MOCK", "").lower() == "true":
        log.info("sns_publish_success", order_id=order_id, source="mock")
        return

    topic_arn = os.environ.get("SNS_TOPIC_ARN", "")
    if not topic_arn:
        log.error("sns_topic_arn_missing", order_id=order_id)
        raise RuntimeError("SNS_TOPIC_ARN environment variable is not set")

    try:
        resp = _get_sns().publish(
            TopicArn=topic_arn,
            Subject=subject,
            Message=message,
        )
        log.info(
            "sns_publish_success",
            order_id=order_id,
            message_id=resp.get("MessageId", ""),
        )
    except Exception as exc:
        log.error("sns_publish_failure", order_id=order_id, error=str(exc))
        raise  # Re-raise so SQS retries the message


def handler(event: dict, context: Any) -> None:
    records = event.get("Records", [])
    log.info("notification_handler_invoked", record_count=len(records))

    for record in records:
        _process_record(record)

    log.info("notification_handler_complete", record_count=len(records))
