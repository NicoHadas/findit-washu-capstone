import json
import os
import uuid
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")
sqs = boto3.client("sqs")

TABLE_NAME = os.environ["TABLE_NAME"]
QUEUE_URL = os.environ["QUEUE_URL"]

table = dynamodb.Table(TABLE_NAME)


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS"
        },
        "body": json.dumps(body)
    }


def lambda_handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method")
    path = event.get("rawPath", "")

    if method == "OPTIONS":
        return response(200, {"ok": True})

    if method == "GET" and path == "/items":
        result = table.scan()
        items = result.get("Items", [])
        items = sorted(items, key=lambda x: x.get("createdAt", ""), reverse=True)
        return response(200, {"items": items})

    if method == "POST" and path == "/items":
        try:
            body = json.loads(event.get("body") or "{}")
        except json.JSONDecodeError:
            return response(400, {"error": "Invalid JSON body"})

        required_fields = ["itemType", "category", "description", "location", "contact"]
        missing = [field for field in required_fields if not body.get(field)]

        if missing:
            return response(400, {"error": f"Missing required fields: {', '.join(missing)}"})

        item_type = body["itemType"].lower().strip()
        if item_type not in ["lost", "found"]:
            return response(400, {"error": "itemType must be either lost or found"})

        now = datetime.now(timezone.utc).isoformat()
        item_id = str(uuid.uuid4())

        item = {
            "itemId": item_id,
            "itemType": item_type,
            "category": body["category"].lower().strip(),
            "description": body["description"].strip(),
            "location": body["location"].strip(),
            "contact": body["contact"].strip(),
            "status": "open",
            "createdAt": now,
            "matches": []
        }

        # Save listing to DynamoDB
        table.put_item(Item=item)

        # Send async match-check job to SQS
        sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps({
                "itemId": item_id,
                "itemType": item_type,
                "category": item["category"],
                "description": item["description"],
                "location": item["location"]
            })
        )

        return response(201, {
            "message": "Item created and match check queued",
            "item": item
        })

    return response(404, {"error": "Route not found"})
