#!/usr/bin/env python3
"""
Cloud Posture — LocalStack Bootstrap Script
Creates fake AWS resources in LocalStack simulating a real enterprise AWS organisation
across 3 accounts for the full 50-sprint product roadmap.

Run AFTER LocalStack is healthy:
  docker-compose -f docker-compose.localstack.yml up -d
  python3 bootstrap_localstack.py
"""

import boto3
import json
import time
import sys
from botocore.config import Config
from botocore.exceptions import ClientError

# ─── LocalStack connection config ───────────────────────────────────────────
ENDPOINT = "http://localhost:4566"
AWS_REGION = "us-east-1"
BOTO_CONFIG = Config(retries={"max_attempts": 3, "mode": "standard"})

COMMON_KWARGS = dict(
    endpoint_url=ENDPOINT,
    aws_access_key_id="test",
    aws_secret_access_key="test",
    region_name=AWS_REGION,
    config=BOTO_CONFIG,
)

# ─── Account definitions ────────────────────────────────────────────────────
ACCOUNTS = [
    {"id": "123456789012", "name": "prod-account",     "region": "us-east-1"},
    {"id": "234567890123", "name": "dev-account",      "region": "us-west-2"},
    {"id": "345678901234", "name": "security-account", "region": "us-east-1"},
]

def client(service, region=AWS_REGION):
    return boto3.client(service, **{**COMMON_KWARGS, "region_name": region})


def section(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


def safe(fn, *args, **kwargs):
    """Call fn, swallow AlreadyExists / Duplicate errors."""
    try:
        return fn(*args, **kwargs)
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in (
            "BucketAlreadyOwnedByYou", "BucketAlreadyExists",
            "EntityAlreadyExists", "InvalidParameterValue",
            "DBInstanceAlreadyExists", "DBClusterAlreadyExistsFault",
            "ResourceConflictException", "InvalidClientTokenId",
            "AccessDeniedException",
        ):
            print(f"  [skip] {code}: {e.response['Error']['Message'][:80]}")
            return None
        print(f"  [warn] {code}: {e.response['Error']['Message'][:120]}")
        return None


# ════════════════════════════════════════════════════════════════════════════
# S3 BUCKETS
# ════════════════════════════════════════════════════════════════════════════

S3_BUCKETS = [
    # (name, account, public_read, encryption, versioning, notes)
    ("prod-data-lake",          "prod",     True,  False, False, "MISCONFIGURATION: public read ACL"),
    ("prod-customer-pii",       "prod",     False, False, False, "MISCONFIGURATION: no encryption"),
    ("prod-financial-reports",  "prod",     False, True,  False, "MISCONFIGURATION: versioning disabled"),
    ("prod-app-logs",           "prod",     True,  False, False, "MISCONFIGURATION: public"),
    ("prod-backups",            "prod",     False, True,  True,  "MISCONFIGURATION: cross-account access"),
    ("dev-test-data",           "dev",      False, False, False, "contains fake PII objects"),
    ("dev-build-artifacts",     "dev",      True,  False, False, "MISCONFIGURATION: public"),
    ("security-audit-logs",     "security", False, True,  True,  "COMPLIANT"),
    ("prod-static-assets",      "prod",     False, True,  False, "CloudFront origin — OK"),
    ("prod-ml-training-data",   "prod",     False, False, False, "SageMaker — sensitive"),
    ("dev-ml-experiments",      "dev",      True,  False, False, "public notebook data"),
    ("prod-terraform-state",    "prod",     False, True,  True,  "bucket policy too permissive"),
    ("prod-cf-templates",       "prod",     True,  False, False, "MISCONFIGURATION: public"),
    ("prod-media-assets",       "prod",     False, True,  True,  "proper config"),
    ("prod-database-backups",   "prod",     False, False, False, "no lifecycle, no encryption"),
]


def create_s3_buckets():
    section("S3 Buckets")
    s3 = client("s3")
    for name, acct, public_read, encrypt, versioning, notes in S3_BUCKETS:
        print(f"  Creating bucket: {name}  [{notes}]")
        # LocalStack uses us-east-1 for all regardless
        safe(s3.create_bucket, Bucket=name)

        if public_read:
            safe(
                s3.put_bucket_acl,
                Bucket=name,
                ACL="public-read",
            )
            # Also disable public access block so the ACL takes effect
            safe(
                s3.put_public_access_block,
                Bucket=name,
                PublicAccessBlockConfiguration={
                    "BlockPublicAcls": False,
                    "IgnorePublicAcls": False,
                    "BlockPublicPolicy": False,
                    "RestrictPublicBuckets": False,
                },
            )

        if encrypt:
            safe(
                s3.put_bucket_encryption,
                Bucket=name,
                ServerSideEncryptionConfiguration={
                    "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
                },
            )

        if versioning:
            safe(
                s3.put_bucket_versioning,
                Bucket=name,
                VersioningConfiguration={"Status": "Enabled"},
            )

        # Upload fake PII objects to dev-test-data
        if name == "dev-test-data":
            fake_pii = json.dumps(
                [
                    {"name": "John Doe", "email": "john.doe@example.com", "ssn": "123-45-6789", "dob": "1985-03-12", "phone": "555-0100"},
                    {"name": "Jane Smith", "email": "jane.smith@example.com", "ssn": "987-65-4321", "dob": "1990-07-22", "phone": "555-0101"},
                    {"name": "Bob Johnson", "email": "bob.j@example.com", "credit_card": "4111111111111111", "bank_account": "12345678"},
                ]
            )
            safe(s3.put_object, Bucket=name, Key="users/pii_data.json", Body=fake_pii.encode())
            safe(s3.put_object, Bucket=name, Key="medical/patient_records.csv",
                 Body=b"patient_id,diagnosis_code,name\nP001,J45.0,Alice Brown\nP002,E11.9,Charlie Davis")

    print("  S3 buckets done.")


# ════════════════════════════════════════════════════════════════════════════
# VPC / NETWORKING
# ════════════════════════════════════════════════════════════════════════════

def create_networking():
    section("VPC / Networking")
    ec2 = client("ec2")

    # prod-vpc
    prod_vpc_resp = safe(ec2.create_vpc, CidrBlock="10.0.0.0/16",
                         TagSpecifications=[{"ResourceType": "vpc",
                                             "Tags": [{"Key": "Name", "Value": "prod-vpc"}]}])
    prod_vpc_id = prod_vpc_resp["Vpc"]["VpcId"] if prod_vpc_resp else None

    # dev-vpc
    dev_vpc_resp = safe(ec2.create_vpc, CidrBlock="172.16.0.0/16",
                        TagSpecifications=[{"ResourceType": "vpc",
                                            "Tags": [{"Key": "Name", "Value": "dev-vpc"}]}])
    dev_vpc_id = dev_vpc_resp["Vpc"]["VpcId"] if dev_vpc_resp else None

    print(f"  prod-vpc: {prod_vpc_id}  dev-vpc: {dev_vpc_id}")

    subnet_ids = []
    if prod_vpc_id:
        # Public subnets
        for i, cidr in enumerate(["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]):
            r = safe(ec2.create_subnet, VpcId=prod_vpc_id, CidrBlock=cidr,
                     AvailabilityZone=f"us-east-1{'abc'[i]}",
                     TagSpecifications=[{"ResourceType": "subnet",
                                         "Tags": [{"Key": "Name", "Value": f"prod-public-{i+1}"}]}])
            if r:
                subnet_ids.append(r["Subnet"]["SubnetId"])

        # Private subnets
        for i, cidr in enumerate(["10.0.10.0/24", "10.0.11.0/24", "10.0.12.0/24"]):
            r = safe(ec2.create_subnet, VpcId=prod_vpc_id, CidrBlock=cidr,
                     AvailabilityZone=f"us-east-1{'abc'[i]}",
                     TagSpecifications=[{"ResourceType": "subnet",
                                         "Tags": [{"Key": "Name", "Value": f"prod-private-{i+1}"}]}])
            if r:
                subnet_ids.append(r["Subnet"]["SubnetId"])

        # Internet Gateway
        igw = safe(ec2.create_internet_gateway,
                   TagSpecifications=[{"ResourceType": "internet-gateway",
                                       "Tags": [{"Key": "Name", "Value": "prod-igw"}]}])
        if igw:
            safe(ec2.attach_internet_gateway,
                 InternetGatewayId=igw["InternetGateway"]["InternetGatewayId"],
                 VpcId=prod_vpc_id)

    return prod_vpc_id, dev_vpc_id, subnet_ids


# ════════════════════════════════════════════════════════════════════════════
# SECURITY GROUPS
# ════════════════════════════════════════════════════════════════════════════

SG_DEFS = [
    ("sg-prod-web",           "prod-vpc",  [("tcp", 22, "0.0.0.0/0"), ("tcp", 80, "0.0.0.0/0"), ("tcp", 443, "0.0.0.0/0")]),
    ("sg-prod-app",           "prod-vpc",  [("tcp", 8080, "0.0.0.0/0")]),
    ("sg-prod-db",            "prod-vpc",  [("tcp", 3306, "0.0.0.0/0")]),
    ("sg-prod-bastion",       "prod-vpc",  [("tcp", 22, "0.0.0.0/0")]),
    ("sg-dev-open",           "dev-vpc",   [("-1", 0, "0.0.0.0/0")]),
    ("sg-prod-internal",      "prod-vpc",  [("tcp", 443, "10.0.0.0/8")]),
    ("sg-prod-ecs",           "prod-vpc",  [("tcp", 80, "0.0.0.0/0"), ("tcp", 443, "0.0.0.0/0")]),
    ("sg-prod-redis",         "prod-vpc",  [("tcp", 6379, "0.0.0.0/0")]),
    ("sg-prod-elasticsearch", "prod-vpc",  [("tcp", 9200, "0.0.0.0/0")]),
    ("sg-prod-ml",            "prod-vpc",  [("tcp", 8888, "0.0.0.0/0")]),
]


def create_security_groups(prod_vpc_id, dev_vpc_id):
    section("Security Groups")
    ec2 = client("ec2")
    sg_ids = {}

    vpc_map = {"prod-vpc": prod_vpc_id, "dev-vpc": dev_vpc_id}

    for sg_name, vpc_name, rules in SG_DEFS:
        vpc_id = vpc_map.get(vpc_name) or prod_vpc_id
        if not vpc_id:
            continue
        r = safe(ec2.create_security_group,
                 GroupName=sg_name,
                 Description=f"Cloud Posture synthetic SG: {sg_name}",
                 VpcId=vpc_id,
                 TagSpecifications=[{"ResourceType": "security-group",
                                     "Tags": [{"Key": "Name", "Value": sg_name}]}])
        if not r:
            continue
        sg_id = r["GroupId"]
        sg_ids[sg_name] = sg_id
        print(f"  {sg_name}: {sg_id}")

        for proto, port, cidr in rules:
            if proto == "-1":
                safe(ec2.authorize_security_group_ingress,
                     GroupId=sg_id,
                     IpPermissions=[{"IpProtocol": "-1",
                                      "IpRanges": [{"CidrIp": cidr}]}])
            else:
                safe(ec2.authorize_security_group_ingress,
                     GroupId=sg_id,
                     IpPermissions=[{"IpProtocol": proto,
                                      "FromPort": port, "ToPort": port,
                                      "IpRanges": [{"CidrIp": cidr}]}])

    return sg_ids


# ════════════════════════════════════════════════════════════════════════════
# EC2 INSTANCES
# ════════════════════════════════════════════════════════════════════════════

EC2_INSTANCES = [
    ("prod-web-01",  "t3.medium",   True,  "sg-prod-web",  "ami-0abcdef1234567890"),
    ("prod-web-02",  "t3.medium",   True,  "sg-prod-web",  "ami-0abcdef1234567890"),
    ("prod-web-03",  "t3.medium",   True,  "sg-prod-web",  "ami-0abcdef1234567890"),
    ("prod-app-01",  "t3.large",    False, "sg-prod-app",  "ami-0abcdef1234567890"),
    ("prod-app-02",  "t3.large",    False, "sg-prod-app",  "ami-0abcdef1234567890"),
    ("prod-db-01",   "r5.large",    False, "sg-prod-db",   "ami-0abcdef1234567890"),
    ("prod-bastion", "t2.micro",    True,  "sg-prod-bastion", "ami-0abcdef1234567890"),
    ("dev-build-01", "t3.medium",   True,  "sg-dev-open",  "ami-0abcdef1234567890"),
    ("dev-test-01",  "t3.small",    True,  "sg-dev-open",  "ami-0abcdef1234567890"),
    ("dev-test-02",  "t3.small",    True,  "sg-dev-open",  "ami-0abcdef1234567890"),
    ("prod-ml-worker","g4dn.xlarge",True,  "sg-prod-ml",   "ami-0abcdef1234567890"),
    ("prod-ecs-host", "c5.2xlarge", False, "sg-prod-ecs",  "ami-0abcdef1234567890"),
]


def create_ec2_instances(sg_ids, subnet_ids):
    section("EC2 Instances")
    ec2 = client("ec2")
    instance_ids = {}

    default_sg = list(sg_ids.values())[0] if sg_ids else None
    default_subnet = subnet_ids[0] if subnet_ids else None

    for name, itype, public_ip, sg_name, ami in EC2_INSTANCES:
        sg_id = sg_ids.get(sg_name, default_sg)
        kwargs = dict(
            ImageId=ami,
            InstanceType=itype,
            MinCount=1,
            MaxCount=1,
            TagSpecifications=[{"ResourceType": "instance",
                                 "Tags": [{"Key": "Name", "Value": name}]}],
        )
        if sg_id:
            kwargs["SecurityGroupIds"] = [sg_id]
        if default_subnet:
            kwargs["SubnetId"] = default_subnet

        r = safe(ec2.run_instances, **kwargs)
        if r and r.get("Instances"):
            iid = r["Instances"][0]["InstanceId"]
            instance_ids[name] = iid
            print(f"  {name}: {iid}  ({itype}{'  [PUBLIC]' if public_ip else ''})")

    return instance_ids


# ════════════════════════════════════════════════════════════════════════════
# IAM
# ════════════════════════════════════════════════════════════════════════════

IAM_USERS = [
    ("admin-user",        ["arn:aws:iam::aws:policy/AdministratorAccess"],         False),
    ("deploy-user",       ["arn:aws:iam::aws:policy/PowerUserAccess"],             False),
    ("readonly-user",     ["arn:aws:iam::aws:policy/ReadOnlyAccess"],              True),
    ("dev-user-1",        ["arn:aws:iam::aws:policy/AmazonEC2FullAccess"],         False),
    ("dev-user-2",        ["arn:aws:iam::aws:policy/AmazonS3FullAccess"],          False),
    ("dev-user-3",        ["arn:aws:iam::aws:policy/AmazonRDSFullAccess"],         False),
    ("dev-user-4",        ["arn:aws:iam::aws:policy/AWSLambda_FullAccess"],        False),
    ("dev-user-5",        ["arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"],    False),
    ("ci-cd-user",        [],                                                       False),  # inline policy
    ("data-analyst-user", ["arn:aws:iam::aws:policy/AmazonAthenaFullAccess",
                           "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"],      False),
    ("ml-engineer-user",  ["arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"],   False),
]

IAM_ROLES = [
    ("prod-ec2-instance-role",   "ec2.amazonaws.com"),
    ("prod-lambda-execution-role", "lambda.amazonaws.com"),
    ("dev-admin-role",           "ec2.amazonaws.com"),
    ("prod-ecs-task-role",       "ecs-tasks.amazonaws.com"),
    ("cross-account-audit-role", "ec2.amazonaws.com"),
    ("github-actions-role",      "sts.amazonaws.com"),
    ("sagemaker-execution-role", "sagemaker.amazonaws.com"),
    ("prod-deploy-role",         "ec2.amazonaws.com"),
]

CICD_INLINE_POLICY = json.dumps({
    "Version": "2012-10-17",
    "Statement": [
        {"Effect": "Allow", "Action": ["s3:*", "ec2:*", "iam:PassRole"], "Resource": "*"}
    ],
})

OVERPERMISSIONED_EC2_ROLE_POLICY = json.dumps({
    "Version": "2012-10-17",
    "Statement": [
        {"Effect": "Allow", "Action": ["s3:*", "iam:PassRole"], "Resource": "*"}
    ],
})

PRIV_ESC_SAGEMAKER_POLICY = json.dumps({
    "Version": "2012-10-17",
    "Statement": [
        {"Effect": "Allow", "Action": ["iam:CreateRole", "iam:AttachRolePolicy"], "Resource": "*"},
        {"Effect": "Allow", "Action": "sagemaker:*", "Resource": "*"},
    ],
})


def create_iam():
    section("IAM Users and Roles")
    iam = client("iam")

    # Users
    for username, policies, mfa_ok in IAM_USERS:
        safe(iam.create_user, UserName=username,
             Tags=[{"Key": "mfa_required", "Value": str(mfa_ok)}])
        safe(iam.create_access_key, UserName=username)
        for policy_arn in policies:
            safe(iam.attach_user_policy, UserName=username, PolicyArn=policy_arn)

        if username == "ci-cd-user":
            safe(iam.put_user_policy,
                 UserName=username,
                 PolicyName="CICDOverpermissioned",
                 PolicyDocument=CICD_INLINE_POLICY)
        print(f"  user: {username}")

    # Roles
    for role_name, principal in IAM_ROLES:
        if principal == "sts.amazonaws.com":
            # github-actions OIDC — missing condition (CRITICAL MISCONFIGURATION)
            trust = json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"},
                    "Action": "sts:AssumeRoleWithWebIdentity",
                    # NOTE: missing Condition — any GitHub repo can assume this role
                }],
            })
        else:
            trust = json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {"Service": principal},
                    "Action": "sts:AssumeRole",
                }],
            })

        safe(iam.create_role, RoleName=role_name, AssumeRolePolicyDocument=trust,
             Tags=[{"Key": "env", "Value": "prod"}])

        if role_name == "prod-ec2-instance-role":
            safe(iam.put_role_policy, RoleName=role_name,
                 PolicyName="OverpermissionedEC2",
                 PolicyDocument=OVERPERMISSIONED_EC2_ROLE_POLICY)
        elif role_name == "dev-admin-role":
            safe(iam.attach_role_policy, RoleName=role_name,
                 PolicyArn="arn:aws:iam::aws:policy/AdministratorAccess")
        elif role_name == "prod-deploy-role":
            safe(iam.attach_role_policy, RoleName=role_name,
                 PolicyArn="arn:aws:iam::aws:policy/AdministratorAccess")
        elif role_name == "sagemaker-execution-role":
            safe(iam.put_role_policy, RoleName=role_name,
                 PolicyName="PrivEscPath",
                 PolicyDocument=PRIV_ESC_SAGEMAKER_POLICY)
        elif role_name == "prod-lambda-execution-role":
            safe(iam.put_role_policy, RoleName=role_name,
                 PolicyName="OverpermissionedLambda",
                 PolicyDocument=json.dumps({
                     "Version": "2012-10-17",
                     "Statement": [{"Effect": "Allow", "Action": ["ec2:*", "rds:*", "s3:*"], "Resource": "*"}],
                 }))
        print(f"  role: {role_name}")

    print("  IAM done.")


# ════════════════════════════════════════════════════════════════════════════
# RDS
# ════════════════════════════════════════════════════════════════════════════

def create_rds():
    section("RDS Instances")
    rds = client("rds")

    instances = [
        dict(DBInstanceIdentifier="prod-mysql-01", DBInstanceClass="db.t3.medium",
             Engine="mysql", EngineVersion="8.0.32", MasterUsername="admin",
             MasterUserPassword="Password123!", AllocatedStorage=100,
             PubliclyAccessible=True, MultiAZ=False,
             StorageEncrypted=False),  # MISCONFIGS: public + no encryption + no multi-az
        dict(DBInstanceIdentifier="prod-postgres-01", DBInstanceClass="db.t3.medium",
             Engine="postgres", EngineVersion="14.7", MasterUsername="pgadmin",
             MasterUserPassword="SecurePass456!", AllocatedStorage=100,
             PubliclyAccessible=False, MultiAZ=True,
             StorageEncrypted=True),  # COMPLIANT
        dict(DBInstanceIdentifier="dev-mysql-01", DBInstanceClass="db.t3.micro",
             Engine="mysql", EngineVersion="5.7.42", MasterUsername="root",
             MasterUserPassword="devpass!", AllocatedStorage=20,
             PubliclyAccessible=True, MultiAZ=False,
             StorageEncrypted=False),  # OUTDATED + public
        dict(DBInstanceIdentifier="prod-analytics-db", DBInstanceClass="db.t3.large",
             Engine="postgres", EngineVersion="13.8", MasterUsername="analyst",
             MasterUserPassword="AnalyticsPass789!", AllocatedStorage=500,
             PubliclyAccessible=True, MultiAZ=False,
             StorageEncrypted=False),  # publicly accessible analytics
    ]

    for inst in instances:
        safe(rds.create_db_instance, **inst)
        print(f"  RDS: {inst['DBInstanceIdentifier']} ({inst['Engine']} {inst['EngineVersion']})")

    # Aurora cluster
    safe(rds.create_db_cluster,
         DBClusterIdentifier="prod-aurora-cluster",
         Engine="aurora-mysql",
         EngineVersion="8.0.mysql_aurora.3.02.0",
         MasterUsername="admin",
         MasterUserPassword="AuroraSecure!",
         StorageEncrypted=True)
    print("  RDS: prod-aurora-cluster (Aurora MySQL)")
    print("  RDS done.")


# ════════════════════════════════════════════════════════════════════════════
# LAMBDA FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════

LAMBDA_PLACEHOLDER_ZIP = (
    b"PK\x03\x04\x14\x00\x00\x00\x08\x00"  # minimal valid zip
    b"\x00\x00!\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x08\x00\x00\x00index.pyHello!\n"
    b"PK\x01\x02\x14\x00\x14\x00\x00\x00\x08\x00\x00\x00!\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x08\x00\x00\x00\x00\x00index.pyPK\x05\x06"
    b"\x00\x00\x00\x00\x01\x00\x01\x006\x00\x00\x00.\x00\x00\x00\x00\x00"
)


def create_lambda_functions():
    section("Lambda Functions")
    lmb = client("lambda")

    role_arn = "arn:aws:iam::123456789012:role/prod-lambda-execution-role"
    admin_role_arn = "arn:aws:iam::123456789012:role/dev-admin-role"

    functions = [
        dict(FunctionName="prod-api-handler",      Runtime="python3.8",   Role=role_arn,
             Handler="index.handler",
             Environment={"Variables": {"DB_PASSWORD": "SuperSecret123!", "DB_HOST": "prod-mysql-01.rds.amazonaws.com"}}),
        dict(FunctionName="prod-data-processor",   Runtime="nodejs14.x",  Role=role_arn,
             Handler="index.handler", Environment={"Variables": {}}),
        dict(FunctionName="prod-auth-service",     Runtime="python3.11",  Role=role_arn,
             Handler="index.handler", Environment={"Variables": {"SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123456789012:secret/prod-auth-key"}}),
        dict(FunctionName="prod-payment-processor",Runtime="python3.9",   Role=role_arn,
             Handler="index.handler",
             Environment={"Variables": {"STRIPE_API_KEY": "sk_live_HARDCODED_KEY_CRITICAL", "PCI_SCOPE": "true"}}),
        dict(FunctionName="dev-test-function",     Runtime="python3.11",  Role=admin_role_arn,
             Handler="index.handler", Environment={"Variables": {}}),
        dict(FunctionName="prod-image-resizer",    Runtime="python3.9",   Role=role_arn,
             Handler="index.handler", Environment={"Variables": {"PUBLIC_URL": "true"}}),
        dict(FunctionName="prod-etl-job",          Runtime="python3.11",  Role=role_arn,
             Handler="index.handler", Environment={"Variables": {}}),
        dict(FunctionName="prod-ml-inference",     Runtime="python3.9",   Role=role_arn,
             Handler="index.handler", Environment={"Variables": {"SAGEMAKER_ENDPOINT": "prod-ml-endpoint"}}),
    ]

    for fn in functions:
        safe(lmb.create_function,
             **fn,
             Code={"ZipFile": LAMBDA_PLACEHOLDER_ZIP},
             Timeout=30,
             MemorySize=256)
        print(f"  Lambda: {fn['FunctionName']} ({fn['Runtime']})")

    print("  Lambda done.")


# ════════════════════════════════════════════════════════════════════════════
# KMS & SECRETS MANAGER
# ════════════════════════════════════════════════════════════════════════════

def create_kms_and_secrets():
    section("KMS Keys & Secrets Manager")
    kms = client("kms")
    sm = client("secretsmanager")

    # KMS Keys
    overly_permissive_policy = json.dumps({
        "Version": "2012-10-17",
        "Id": "key-default-1",
        "Statement": [
            {
                "Sid": "Enable IAM User Permissions",
                "Effect": "Allow",
                "Principal": {"AWS": "*"},
                "Action": "kms:*",
                "Resource": "*",
            }
        ],
    })

    default_policy = json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": "arn:aws:iam::123456789012:root"},
                "Action": "kms:*",
                "Resource": "*",
            }
        ],
    })

    for i, (desc, policy) in enumerate([
        ("prod-cmk-s3", default_policy),
        ("prod-cmk-rds", default_policy),
        ("prod-cmk-overpermissive", overly_permissive_policy),  # MISCONFIGURATION
    ]):
        r = safe(kms.create_key, Description=desc, Policy=policy,
                 Tags=[{"TagKey": "Name", "TagValue": desc}])
        if r:
            kid = r["KeyMetadata"]["KeyId"]
            safe(kms.create_alias, AliasName=f"alias/{desc}", TargetKeyId=kid)
            print(f"  KMS key: {desc} ({kid})")

    # Secrets Manager
    secrets = [
        ("prod-db-password",   {"username": "admin", "password": "ProdDBPass123!"}, False),
        ("prod-api-key",       {"api_key": "prod-live-key-abc123"},                  False),
        ("prod-stripe-key",    {"key": "sk_live_STRIPE_SECRET"},                    False),
        ("dev-db-password",    {"username": "root", "password": "devpass123"},       True),
        ("prod-oauth-secret",  {"client_secret": "oauth-secret-xyz"},               False),
        ("prod-jwt-secret",    {"secret": "jwt-signing-key-prod"},                  False),
        ("dev-test-credentials",{"username": "testuser", "password": "testpass"},   True),
        ("prod-smtp-password", {"host": "smtp.example.com", "password": "SMTP123"}, False),
        ("prod-datadog-key",   {"api_key": "dd-api-key-prod"},                       False),
        ("prod-github-token",  {"token": "ghp_GITHUB_PAT_TOKEN"},                   False),
    ]

    broad_policy = json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {"Effect": "Allow",
             "Principal": {"AWS": "*"},
             "Action": "secretsmanager:GetSecretValue",
             "Resource": "*"}
        ],
    })

    for i, (name, value, is_dev) in enumerate(secrets):
        policy = broad_policy if i < 2 else None  # first 2 have broad access policies
        kwargs = dict(
            Name=name,
            SecretString=json.dumps(value),
            Tags=[{"Key": "env", "Value": "dev" if is_dev else "prod"}],
        )
        # ResourcePolicy is a separate API call; skip for LocalStack compat
        safe(sm.create_secret, **kwargs)
        print(f"  Secret: {name}")

    print("  KMS + Secrets done.")


# ════════════════════════════════════════════════════════════════════════════
# CLOUDTRAIL
# ════════════════════════════════════════════════════════════════════════════

def create_cloudtrail():
    section("CloudTrail")
    ct = client("cloudtrail")
    s3 = client("s3")

    # Ensure the audit log bucket exists
    safe(s3.create_bucket, Bucket="security-cloudtrail-logs")

    # prod-trail: multi-region disabled, no log file validation
    safe(
        ct.create_trail,
        Name="prod-trail",
        S3BucketName="security-cloudtrail-logs",
        IsMultiRegionTrail=False,        # MISCONFIGURATION
        EnableLogFileValidation=False,   # MISCONFIGURATION
        IncludeGlobalServiceEvents=True,
    )
    safe(ct.start_logging, Name="prod-trail")
    print("  prod-trail created (multi-region=False, log-validation=False — MISCONFIG)")

    # dev-trail: disabled entirely
    safe(
        ct.create_trail,
        Name="dev-trail",
        S3BucketName="security-cloudtrail-logs",
        IsMultiRegionTrail=False,
        EnableLogFileValidation=False,
    )
    # Intentionally NOT calling start_logging — dev-trail is disabled
    print("  dev-trail created but NOT started — CRITICAL MISCONFIGURATION")

    print("  CloudTrail done.")


# ════════════════════════════════════════════════════════════════════════════
# ECS / EKS
# ════════════════════════════════════════════════════════════════════════════

def create_ecs():
    section("ECS")
    ecs = client("ecs")

    safe(ecs.create_cluster, clusterName="prod-ecs-cluster",
         tags=[{"key": "env", "value": "prod"}])
    print("  ECS cluster: prod-ecs-cluster")

    # Task definition with privileged=true — CRITICAL MISCONFIGURATION
    safe(
        ecs.register_task_definition,
        family="prod-privileged-task",
        networkMode="awsvpc",
        containerDefinitions=[
            {
                "name": "prod-app-container",
                "image": "nginx:latest",
                "privileged": True,   # CRITICAL MISCONFIGURATION
                "portMappings": [{"containerPort": 80, "protocol": "tcp"}],
            }
        ],
        requiresCompatibilities=["FARGATE"],
        cpu="256",
        memory="512",
    )
    print("  ECS task: prod-privileged-task (privileged=true — CRITICAL)")

    safe(
        ecs.register_task_definition,
        family="prod-normal-task",
        networkMode="awsvpc",
        containerDefinitions=[
            {
                "name": "prod-app-container",
                "image": "nginx:latest",
                "privileged": False,
                "portMappings": [{"containerPort": 443, "protocol": "tcp"}],
            }
        ],
        requiresCompatibilities=["FARGATE"],
        cpu="512",
        memory="1024",
    )
    print("  ECS task: prod-normal-task (properly configured)")
    print("  ECS done.")


# ════════════════════════════════════════════════════════════════════════════
# CLOUDWATCH (missing alarms — MISCONFIGURATIONS)
# ════════════════════════════════════════════════════════════════════════════

def create_cloudwatch():
    section("CloudWatch")
    cw = client("cloudwatch")
    logs = client("logs")

    # Create log group (but intentionally create NO critical security alarms)
    safe(logs.create_log_group, logGroupName="/aws/cloudtrail/prod")
    safe(logs.create_log_group, logGroupName="/aws/lambda/prod-api-handler")
    safe(logs.create_log_group, logGroupName="/aws/ecs/prod-ecs-cluster")

    # Only create a non-critical alarm — missing: root login, MFA, unauthorized API calls
    safe(
        cw.put_metric_alarm,
        AlarmName="prod-high-cpu",
        MetricName="CPUUtilization",
        Namespace="AWS/EC2",
        Statistic="Average",
        Period=300,
        EvaluationPeriods=2,
        Threshold=80.0,
        ComparisonOperator="GreaterThanThreshold",
        AlarmDescription="High CPU — not a security alarm",
    )
    print("  CloudWatch: Only non-security alarms created.")
    print("  MISSING: root-account-login-alarm, unauthorized-api-calls-alarm, console-login-without-mfa-alarm")
    print("  CloudWatch done.")


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

def wait_for_localstack():
    import urllib.request
    print("Waiting for LocalStack to be ready...")
    for _ in range(30):
        try:
            urllib.request.urlopen("http://localhost:4566/_localstack/health", timeout=3)
            print("LocalStack is ready.")
            return True
        except Exception:
            time.sleep(2)
    print("ERROR: LocalStack did not become ready in time.")
    return False


def main():
    print("=" * 60)
    print("  Cloud Posture — LocalStack Bootstrap")
    print("=" * 60)

    if not wait_for_localstack():
        sys.exit(1)

    create_s3_buckets()
    prod_vpc_id, dev_vpc_id, subnet_ids = create_networking()
    sg_ids = create_security_groups(prod_vpc_id, dev_vpc_id)
    instance_ids = create_ec2_instances(sg_ids, subnet_ids)
    create_iam()
    create_rds()
    create_lambda_functions()
    create_kms_and_secrets()
    create_cloudtrail()
    create_ecs()
    create_cloudwatch()

    section("Bootstrap Complete")
    print(f"  S3 Buckets: {len(S3_BUCKETS)}")
    print(f"  EC2 Instances: {len(EC2_INSTANCES)}")
    print(f"  IAM Users: {len(IAM_USERS)}")
    print(f"  IAM Roles: {len(IAM_ROLES)}")
    print(f"  Security Groups: {len(SG_DEFS)}")
    print()
    print("All LocalStack resources created successfully.")
    print("Next step: python3 generate_synthetic_data.py")


if __name__ == "__main__":
    main()
