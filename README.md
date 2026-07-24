# FindIt WashU

FindIt WashU is a simple lost-and-found web app for campus items. Users can log in, post items they lost or found, and browse current listings.

Live app:

https://d2tsgvc3pen7pg.cloudfront.net

## What it does

A user can submit a listing with:

- lost or found status
- category
- description
- location
- contact info

When a new listing is submitted, the app saves it and starts a background match check. For this demo, matching is based on opposite item type and the same category.

For example, a lost electronics item can match a found electronics item.

## Architecture

The app uses:

- CloudFront for the HTTPS frontend URL
- S3 for the static frontend files
- Auth0 for login
- API Gateway for the backend API
- Lambda for the API logic
- DynamoDB for the lost-and-found listings
- SQS for background match jobs
- Worker Lambda for matching
- Firebase Firestore for a small activity log
- CDK for infrastructure as code

## Basic flow

1. User opens the CloudFront URL.
2. User logs in with Auth0.
3. User submits a lost or found item.
4. API Lambda saves the item in DynamoDB.
5. API Lambda sends a message to SQS.
6. Worker Lambda checks for possible matches.
7. Firebase records a small activity log entry.

## Setup

Install dependencies:

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

Deploy with CDK:

    cdk deploy

After deployment, use the CloudFront output as the live app URL.

## Notes

DynamoDB is the main database. Firebase is only used as the required third-party SaaS integration for the demo.

The matching logic is intentionally simple for the MVP. A future version could add dropdown categories, better location handling, and fuzzy matching.
