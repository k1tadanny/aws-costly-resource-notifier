import os
import logging
import json
import boto3

log_level = os.environ.get("LOG_LEVEL")
aggregator_name = os.environ.get("AGGREGATOR_NAME")
topic_arn = os.environ.get("TOPIC_ARN")

logger = logging.getLogger()
logger.setLevel(log_level)


def lambda_handler(event, context):
    config = boto3.client("config")

    resource_definitions = {
        "RunningRDSInstances": {
            "query": """
                SELECT resourceName, awsRegion, accountId
                WHERE resourceType = 'AWS::RDS::DBInstance'
                    AND configuration.dBInstanceStatus = 'available'
            """,
            "field_order": ["resourceName", "awsRegion", "accountId"]
        },
        "RunningEC2Instances": {
            "query": """
                SELECT tags, resourceId, awsRegion, accountId
                WHERE resourceType = 'AWS::EC2::Instance'
                    AND configuration.state.name = 'running'
            """,
            "field_order": ["tags.Name", "resourceId", "awsRegion", "accountId"]
        },
        "NATGateways": {
            "query": """
                SELECT tags, resourceId, awsRegion, accountId
                WHERE resourceType = 'AWS::EC2::NatGateway'
            """,
            "field_order": ["tags.Name", "resourceId", "awsRegion", "accountId"]
        },
        "LoadBalancers": {
            "query": """
                SELECT resourceName, awsRegion, accountId
                WHERE resourceType = 'AWS::ElasticLoadBalancingV2::LoadBalancer'
            """,
            "field_order": ["resourceName", "awsRegion", "accountId"]
        },
        "InterfaceVPCEndpoints": {
            "query": """
                SELECT tags, resourceId, awsRegion, accountId
                WHERE resourceType = 'AWS::EC2::VPCEndpoint'
                    AND configuration.vpcEndpointType = 'Interface'
            """,
            "field_order": ["tags.Name", "resourceId", "awsRegion", "accountId"]
        },
        "UnassociatedEIPs": {
            "query": """
                SELECT tags, resourceId, awsRegion, accountId
                WHERE resourceType = 'AWS::EC2::EIP'
                    AND configuration.associationId NOT LIKE 'eipassoc-%'
            """,
            "field_order": ["tags.Name", "resourceId", "awsRegion", "accountId"]
        }
    }
    # `IS NULL` is not supported in advanced queries
    # `tags.Name` key is not supported in advanced queries

    results = {}

    for resource_type, resource_definition in resource_definitions.items():
        results[resource_type] = []
        next_token = None

        logger.debug("Resource type: %s", resource_type)

        while True:
            if next_token:
                response = config.select_aggregate_resource_config(
                    ConfigurationAggregatorName=aggregator_name,
                    Expression=resource_definition["query"],
                    NextToken=next_token
                )
            else:
                response = config.select_aggregate_resource_config(
                    ConfigurationAggregatorName=aggregator_name,
                    Expression=resource_definition["query"]
                )

            logger.debug("Response:")
            logger.debug(json.dumps(response))

            items = [json.loads(result) for result in response.get("Results", [])]

            for item in items:
                logger.debug("Item:")
                logger.debug(json.dumps(item))

                if "tags" in item:
                    name_tag = next((tag["value"] for tag in item["tags"] if tag["key"] == "Name"), None)
                    item["tags.Name"] = name_tag
                    del item["tags"]

                ordered_item = {field: item[field] for field in resource_definition["field_order"]}

                results[resource_type].append(ordered_item)

            next_token = response.get("NextToken")
            if not next_token:
                break

    logger.info("Results:")
    logger.info(json.dumps(results))

    message_body = "組織内のAWSアカウントに料金の掛かるリソースが存在します。不要なリソースがあれば削除してください。\n\n"
    message_body += json.dumps(results, indent=2)

    sns = boto3.client("sns")
    sns.publish(
        TopicArn=topic_arn,
        Subject="不要リソース削除のお願い",
        Message=message_body
    )

    return
