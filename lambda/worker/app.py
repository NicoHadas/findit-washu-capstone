import json
import os

import boto3

dynamodb = boto3.resource("dynamodb")

TABLE_NAME = os.environ["TABLE_NAME"]
table = dynamodb.Table(TABLE_NAME)


def lambda_handler(event, context):
    print("Worker received event:")
    print(json.dumps(event))

    for record in event.get("Records", []):
        body = json.loads(record["body"])

        new_item_id = body["itemId"]
        new_item_type = body["itemType"]
        category = body["category"]

        opposite_type = "found" if new_item_type == "lost" else "lost"

        # Simple demo matching:
        # same category + opposite type + open status
        result = table.scan(
            FilterExpression="itemType = :opposite AND category = :category AND #s = :open_status",
            ExpressionAttributeNames={
                "#s": "status"
            },
            ExpressionAttributeValues={
                ":opposite": opposite_type,
                ":category": category,
                ":open_status": "open"
            }
        )

        possible_matches = [
            item for item in result.get("Items", [])
            if item.get("itemId") != new_item_id
        ]

        match_ids = [item["itemId"] for item in possible_matches]

        table.update_item(
            Key={"itemId": new_item_id},
            UpdateExpression="SET matches = :matches",
            ExpressionAttributeValues={
                ":matches": match_ids
            }
        )

        print({
            "newItemId": new_item_id,
            "newItemType": new_item_type,
            "category": category,
            "matchCount": len(match_ids),
            "matchIds": match_ids
        })

    return {"statusCode": 200}
