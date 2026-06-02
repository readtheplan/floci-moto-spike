"""Fake AWS resource simulator using Moto — provisions 11 AWS resource types."""
import json
from typing import Any

import boto3
from moto import mock_aws

RESOURCE_TYPES = {
    "aws_s3_bucket": {
        "provider": "aws",
        "aws_service": "s3",
        "terraform_address_template": "aws_s3_bucket.{name}",
    },
    "aws_dynamodb_table": {
        "provider": "aws",
        "aws_service": "dynamodb",
        "terraform_address_template": "aws_dynamodb_table.{name}",
    },
    "aws_iam_role": {
        "provider": "aws",
        "aws_service": "iam",
        "terraform_address_template": "aws_iam_role.{name}",
    },
    "aws_kms_key": {
        "provider": "aws",
        "aws_service": "kms",
        "terraform_address_template": "aws_kms_key.{name}",
    },
    "aws_db_instance": {
        "provider": "aws",
        "aws_service": "rds",
        "terraform_address_template": "aws_db_instance.{name}",
    },
    "aws_lambda_function": {
        "provider": "aws",
        "aws_service": "lambda",
        "terraform_address_template": "aws_lambda_function.{name}",
    },
    "aws_lb": {
        "provider": "aws",
        "aws_service": "elbv2",
        "terraform_address_template": "aws_lb.{name}",
    },
    "aws_ecs_service": {
        "provider": "aws",
        "aws_service": "ecs",
        "terraform_address_template": "aws_ecs_service.{name}",
    },
    "aws_security_group": {
        "provider": "aws",
        "aws_service": "ec2",
        "terraform_address_template": "aws_security_group.{name}",
    },
    "aws_route53_zone": {
        "provider": "aws",
        "aws_service": "route53",
        "terraform_address_template": "aws_route53_zone.{name}",
    },
    "aws_cloudwatch_log_group": {
        "provider": "aws",
        "aws_service": "logs",
        "terraform_address_template": "aws_cloudwatch_log_group.{name}",
    },
}

class FakeAwsSimulator:
    """Start Moto mocks, call boto3, produce resource records."""

    def __init__(self, region: str = "us-east-1") -> None:
        self.region = region
        self._mock = mock_aws()
        self._clients: dict[str, Any] = {}

    def start(self) -> None:
        self._mock.start()
        self._clients = {
            "s3": boto3.client("s3", region_name=self.region),
            "dynamodb": boto3.client("dynamodb", region_name=self.region),
            "iam": boto3.client("iam", region_name=self.region),
            "kms": boto3.client("kms", region_name=self.region),
            "rds": boto3.client("rds", region_name=self.region),
            "lambda": boto3.client("lambda", region_name=self.region),
            "elbv2": boto3.client("elbv2", region_name=self.region),
            "ecs": boto3.client("ecs", region_name=self.region),
            "ec2": boto3.client("ec2", region_name=self.region),
            "route53": boto3.client("route53", region_name=self.region),
            "logs": boto3.client("logs", region_name=self.region),
        }

    def stop(self) -> None:
        self._mock.stop()

    def provision(self, spec: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Create resources from a spec and return their attributes.

        Each spec entry: {"type": "aws_s3_bucket", "name": "my-bucket", ...}
        Returns list of {"type": ..., "attributes": {...}, "address": "..."}
        """
        resources: list[dict[str, Any]] = []
        for item in spec:
            rtype = item["type"]
            if rtype not in RESOURCE_TYPES:
                raise ValueError(
                    f"Unsupported resource type: {rtype}. "
                    f"Supported: {list(RESOURCE_TYPES)}"
                )
            handler = getattr(self, f"_create_{rtype.replace('aws_', '')}", None)
            if handler is None:
                raise ValueError(f"No handler for {rtype}")
            attrs = handler(item)
            info = RESOURCE_TYPES[rtype]
            address = info["terraform_address_template"].format(name=item["name"])
            resources.append({
                "type": rtype,
                "address": address,
                "attributes": attrs,
            })
        return resources

    # -- resource handlers --

    def _create_s3_bucket(self, spec: dict[str, Any]) -> dict[str, Any]:
        bucket_name = spec["name"]
        self._clients["s3"].create_bucket(Bucket=bucket_name)
        return {"bucket": bucket_name, "region": self.region}

    def _create_dynamodb_table(self, spec: dict[str, Any]) -> dict[str, Any]:
        table_name = spec["name"]
        hash_key = spec.get("hash_key", "id")
        billing_mode = spec.get("billing_mode", "PAY_PER_REQUEST")
        self._clients["dynamodb"].create_table(
            TableName=table_name,
            KeySchema=[{"AttributeName": hash_key, "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": hash_key, "AttributeType": "S"}],
            BillingMode=billing_mode,
        )
        return {
            "name": table_name,
            "hash_key": hash_key,
            "billing_mode": billing_mode,
            "region": self.region,
        }

    def _create_iam_role(self, spec: dict[str, Any]) -> dict[str, Any]:
        role_name = spec["name"]
        assume_policy = spec.get("assume_role_policy", json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "ec2.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }],
        }))
        self._clients["iam"].create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=assume_policy,
        )
        return {"name": role_name, "region": self.region}

    def _create_kms_key(self, spec: dict[str, Any]) -> dict[str, Any]:
        key_alias = spec["name"]
        description = spec.get("description", f"KMS key for {key_alias}")
        resp = self._clients["kms"].create_key(
            Description=description,
            KeyUsage="ENCRYPT_DECRYPT",
        )
        key_id = resp["KeyMetadata"]["KeyId"]
        # Create alias
        self._clients["kms"].create_alias(
            AliasName=f"alias/{key_alias}",
            TargetKeyId=key_id,
        )
        return {
            "alias": key_alias,
            "key_id": key_id,
            "description": description,
            "region": self.region,
        }

    def _create_db_instance(self, spec: dict[str, Any]) -> dict[str, Any]:
        db_id = spec["name"]
        engine = spec.get("engine", "postgres")
        instance_class = spec.get("instance_class", "db.t3.micro")
        allocated_storage = spec.get("allocated_storage", 20)
        username = spec.get("username", "admin")
        password = spec.get("password", "Password123!")
        resp = self._clients["rds"].create_db_instance(
            DBInstanceIdentifier=db_id,
            DBInstanceClass=instance_class,
            Engine=engine,
            AllocatedStorage=allocated_storage,
            MasterUsername=username,
            MasterUserPassword=password,
        )
        db = resp["DBInstance"]
        return {
            "identifier": db_id,
            "engine": engine,
            "instance_class": instance_class,
            "allocated_storage": allocated_storage,
            "region": self.region,
        }

    def _create_lambda_function(self, spec: dict[str, Any]) -> dict[str, Any]:
        fn_name = spec["name"]
        runtime = spec.get("runtime", "python3.11")
        handler = spec.get("handler", "index.handler")
        # Create an IAM role for Lambda if one isn't explicitly provided
        role_name = spec.get("role_name", f"{fn_name}-lambda-role")
        try:
            self._clients["iam"].get_role(RoleName=role_name)
        except Exception:
            self._clients["iam"].create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps({
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Effect": "Allow",
                        "Principal": {"Service": "lambda.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    }],
                }),
            )
        role_arn = spec.get("role_arn", f"arn:aws:iam::123456789012:role/{role_name}")
        # moto lambda requires a zip file; create a minimal one inline
        import io
        import zipfile
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("index.py", "def handler(event, context):\n    return {'statusCode': 200}")
        buf.seek(0)
        resp = self._clients["lambda"].create_function(
            FunctionName=fn_name,
            Runtime=runtime,
            Role=role_arn,
            Handler=handler,
            Code={"ZipFile": buf.read()},
            Timeout=30,
            MemorySize=128,
        )
        return {
            "function_name": fn_name,
            "runtime": runtime,
            "handler": handler,
            "memory_size": 128,
            "timeout": 30,
            "region": self.region,
        }

    def _create_lb(self, spec: dict[str, Any]) -> dict[str, Any]:
        lb_name = spec["name"]
        scheme = spec.get("scheme", "internet-facing")
        lb_type = spec.get("lb_type", "application")
        # Create a VPC + subnets for the ALB if moto requires real ones
        vpc_cidr = spec.get("vpc_cidr", "10.0.0.0/16")
        vpc_resp = self._clients["ec2"].create_vpc(CidrBlock=vpc_cidr)
        vpc_id = vpc_resp["Vpc"]["VpcId"]
        # Create subnets in two AZs
        subnet_ids = []
        for i, az in enumerate(["us-east-1a", "us-east-1b"]):
            subnet_resp = self._clients["ec2"].create_subnet(
                VpcId=vpc_id,
                CidrBlock=f"10.0.{i}.0/24",
                AvailabilityZone=az,
            )
            subnet_ids.append(subnet_resp["Subnet"]["SubnetId"])
        subnets = spec.get("subnets", subnet_ids)
        resp = self._clients["elbv2"].create_load_balancer(
            Name=lb_name,
            Subnets=subnets,
            Scheme=scheme,
            Type=lb_type,
            IpAddressType="ipv4",
        )
        lb = resp["LoadBalancers"][0]
        return {
            "name": lb_name,
            "dns_name": lb.get("DNSName", ""),
            "scheme": scheme,
            "type": lb_type,
            "region": self.region,
        }

    def _create_ecs_service(self, spec: dict[str, Any]) -> dict[str, Any]:
        svc_name = spec["name"]
        cluster = spec.get("cluster", "default")
        desired_count = spec.get("desired_count", 1)
        task_family = spec.get("task_family", "app-task")
        task_revision = spec.get("task_revision", "1")
        task_def = spec.get("task_definition", f"{task_family}:{task_revision}")
        # Register a task definition first
        try:
            self._clients["ecs"].describe_task_definition(taskDefinition=task_def)
        except Exception:
            self._clients["ecs"].register_task_definition(
                family=task_family,
                containerDefinitions=[{
                    "name": "app",
                    "image": "nginx:latest",
                    "memory": 256,
                    "cpu": 256,
                    "essential": True,
                }],
                requiresCompatibilities=["FARGATE"],
                networkMode="awsvpc",
                cpu="256",
                memory="512",
            )
        # Create cluster first
        self._clients["ecs"].create_cluster(clusterName=cluster)
        # Create VPC + subnets for network configuration
        vpc_resp = self._clients["ec2"].create_vpc(CidrBlock="10.1.0.0/16")
        vpc_id = vpc_resp["Vpc"]["VpcId"]
        subnet_resp = self._clients["ec2"].create_subnet(
            VpcId=vpc_id,
            CidrBlock="10.1.1.0/24",
            AvailabilityZone="us-east-1a",
        )
        subnet_id = subnet_resp["Subnet"]["SubnetId"]
        resp = self._clients["ecs"].create_service(
            cluster=cluster,
            serviceName=svc_name,
            taskDefinition=task_def,
            desiredCount=desired_count,
            launchType="FARGATE",
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": [subnet_id],
                    "securityGroups": [],
                    "assignPublicIp": "ENABLED",
                }
            },
        )
        svc = resp["service"]
        return {
            "name": svc_name,
            "cluster": cluster,
            "task_definition": task_def,
            "desired_count": desired_count,
            "region": self.region,
        }

    def _create_security_group(self, spec: dict[str, Any]) -> dict[str, Any]:
        sg_name = spec["name"]
        description = spec.get("description", f"Security group {sg_name}")
        vpc_id = spec.get("vpc_id", "vpc-abc123")
        resp = self._clients["ec2"].create_security_group(
            GroupName=sg_name,
            Description=description,
            VpcId=vpc_id,
        )
        sg_id = resp["GroupId"]
        # Optionally add ingress rules
        ingress = spec.get("ingress_rules", [])
        if ingress:
            self._clients["ec2"].authorize_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=ingress,
            )
        return {
            "name": sg_name,
            "group_id": sg_id,
            "description": description,
            "vpc_id": vpc_id,
            "region": self.region,
        }

    def _create_route53_zone(self, spec: dict[str, Any]) -> dict[str, Any]:
        zone_name = spec["name"]
        comment = spec.get("comment", f"Hosted zone for {zone_name}")
        resp = self._clients["route53"].create_hosted_zone(
            Name=zone_name,
            CallerReference=f"floci-{zone_name}",
            HostedZoneConfig={"Comment": comment, "PrivateZone": False},
        )
        zone = resp["HostedZone"]
        return {
            "name": zone_name,
            "zone_id": zone["Id"].replace("/hostedzone/", ""),
            "comment": comment,
            "region": self.region,
        }

    def _create_cloudwatch_log_group(self, spec: dict[str, Any]) -> dict[str, Any]:
        log_name = spec["name"]
        retention = spec.get("retention_in_days", 30)
        self._clients["logs"].create_log_group(logGroupName=log_name)
        self._clients["logs"].put_retention_policy(
            logGroupName=log_name,
            retentionInDays=retention,
        )
        return {
            "name": log_name,
            "retention_in_days": retention,
            "region": self.region,
        }
