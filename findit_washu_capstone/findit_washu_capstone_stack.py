from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
    aws_dynamodb as dynamodb,
    aws_sqs as sqs,
    aws_lambda as _lambda,
    aws_lambda_event_sources as lambda_event_sources,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as integrations,
    aws_apigatewayv2_authorizers as authorizers,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
)
from constructs import Construct


class FinditWashuCapstoneStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # DynamoDB table
        items_table = dynamodb.Table(
            self,
            "FindItItemsTable",
            partition_key=dynamodb.Attribute(
                name="itemId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        # SQS queue with dead-letter queue
        dlq = sqs.Queue(
            self,
            "FindItMatchDLQ",
            retention_period=Duration.days(14),
            removal_policy=RemovalPolicy.DESTROY
        )

        match_queue = sqs.Queue(
            self,
            "FindItMatchQueue",
            visibility_timeout=Duration.seconds(60),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=dlq
            ),
            removal_policy=RemovalPolicy.DESTROY
        )

        # API Lambda
        api_lambda = _lambda.Function(
            self,
            "FindItApiLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="app.lambda_handler",
            code=_lambda.Code.from_asset("lambda/api_handler"),
            timeout=Duration.seconds(10),
            memory_size=128,
            environment={
                "TABLE_NAME": items_table.table_name,
                "QUEUE_URL": match_queue.queue_url
            }
        )

        # Worker Lambda
        worker_lambda = _lambda.Function(
            self,
            "FindItWorkerLambda",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="app.lambda_handler",
            code=_lambda.Code.from_asset("lambda/worker"),
            timeout=Duration.seconds(30),
            memory_size=128,
            environment={
                "TABLE_NAME": items_table.table_name
            }
        )

        worker_lambda.add_event_source(
            lambda_event_sources.SqsEventSource(
                match_queue,
                batch_size=1
            )
        )

        # IAM least privilege
        items_table.grant_read_write_data(api_lambda)
        items_table.grant_read_write_data(worker_lambda)
        match_queue.grant_send_messages(api_lambda)
        match_queue.grant_consume_messages(worker_lambda)

        # API Gateway + Auth0 JWT authorizer
        auth0_authorizer = authorizers.HttpJwtAuthorizer(
            "FindItAuth0Authorizer",
            jwt_issuer="https://dev-eup7xtvmykcawtzt.us.auth0.com/",
            jwt_audience=["https://findit-washu-api"]
        )

        http_api = apigwv2.HttpApi(
            self,
            "FindItHttpApi",
            cors_preflight=apigwv2.CorsPreflightOptions(
                allow_origins=["*"],
                allow_methods=[
                    apigwv2.CorsHttpMethod.GET,
                    apigwv2.CorsHttpMethod.POST,
                    apigwv2.CorsHttpMethod.OPTIONS
                ],
                allow_headers=["Content-Type", "Authorization"]
            )
        )

        api_integration = integrations.HttpLambdaIntegration(
            "FindItApiIntegration",
            api_lambda
        )

        http_api.add_routes(
            path="/items",
            methods=[
                apigwv2.HttpMethod.GET,
                apigwv2.HttpMethod.POST
            ],
            integration=api_integration,
            authorizer=auth0_authorizer
        )

        # S3 static frontend storage
        website_bucket = s3.Bucket(
            self,
            "FindItWebsiteBucket",
            website_index_document="index.html",
            public_read_access=True,
            block_public_access=s3.BlockPublicAccess(
                block_public_acls=False,
                ignore_public_acls=False,
                block_public_policy=False,
                restrict_public_buckets=False
            ),
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # CloudFront HTTPS frontend delivery
        distribution = cloudfront.Distribution(
            self,
            "FindItCloudFrontDistribution",
            default_root_object="index.html",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(website_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED
            )
        )

        # Deploy frontend files and invalidate CloudFront cache
        s3deploy.BucketDeployment(
            self,
            "DeployFindItFrontend",
            sources=[s3deploy.Source.asset("frontend")],
            destination_bucket=website_bucket,
            distribution=distribution,
            distribution_paths=["/*"]
        )

        # Outputs
        CfnOutput(
            self,
            "ApiUrl",
            value=http_api.api_endpoint,
            description="API Gateway endpoint"
        )

        CfnOutput(
            self,
            "S3WebsiteUrl",
            value=website_bucket.bucket_website_url,
            description="Original S3 website URL. HTTP only."
        )

        CfnOutput(
            self,
            "CloudFrontUrl",
            value=f"https://{distribution.distribution_domain_name}",
            description="HTTPS frontend URL for the live app"
        )

        CfnOutput(
            self,
            "ItemsTableName",
            value=items_table.table_name,
            description="DynamoDB table name"
        )

        CfnOutput(
            self,
            "MatchQueueUrl",
            value=match_queue.queue_url,
            description="SQS queue URL"
        )
