#!/usr/bin/env python3
"""
Cloud Posture — Enterprise Synthetic Data Generator
Simulates a real Fortune-500 AWS environment with 500+ security findings
covering the full 50-sprint product roadmap.
"""
import uuid
import json
import random
from datetime import datetime, timedelta

# ─── Constants ───────────────────────────────────────────────────────────────
WORKSPACE_ID = "7ed72074-8a71-4062-9a3c-55fc195dd878"
PROD_ACCOUNT_UUID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
DEV_ACCOUNT_UUID  = "b2c3d4e5-f6a7-8901-bcde-f12345678901"
SEC_ACCOUNT_UUID  = "c3d4e5f6-a7b8-9012-cdef-123456789012"

PROD_ACCOUNT_ID = "123456789012"
DEV_ACCOUNT_ID  = "234567890123"
SEC_ACCOUNT_ID  = "345678901234"

NOW = datetime.utcnow()

def uid(): return str(uuid.uuid4())
def days_ago(n): return (NOW - timedelta(days=n)).isoformat()
def strip(u): return u.replace("-", "")

# ─── Resource ARN helpers ────────────────────────────────────────────────────
def s3_arn(bucket): return f"arn:aws:s3:::{bucket}"
def ec2_arn(iid, region="us-east-1", acct=PROD_ACCOUNT_ID):
    return f"arn:aws:ec2:{region}:{acct}:instance/{iid}"
def iam_user_arn(user, acct=PROD_ACCOUNT_ID):
    return f"arn:aws:iam::{acct}:user/{user}"
def iam_role_arn(role, acct=PROD_ACCOUNT_ID):
    return f"arn:aws:iam::{acct}:role/{role}"
def rds_arn(db, region="us-east-1", acct=PROD_ACCOUNT_ID):
    return f"arn:aws:rds:{region}:{acct}:db:{db}"
def lambda_arn(fn, region="us-east-1", acct=PROD_ACCOUNT_ID):
    return f"arn:aws:lambda:{region}:{acct}:function:{fn}"
def sg_arn(sg, region="us-east-1", acct=PROD_ACCOUNT_ID):
    return f"arn:aws:ec2:{region}:{acct}:security-group/{sg}"
def trail_arn(name, region="us-east-1", acct=PROD_ACCOUNT_ID):
    return f"arn:aws:cloudtrail:{region}:{acct}:trail/{name}"
def secret_arn(name, region="us-east-1", acct=PROD_ACCOUNT_ID):
    return f"arn:aws:secretsmanager:{region}:{acct}:secret:{name}"

# ─── EC2 instance IDs (fake but realistic) ──────────────────────────────────
EC2_IDS = {
    "prod-web-01":   "i-0a1b2c3d4e5f00001",
    "prod-web-02":   "i-0a1b2c3d4e5f00002",
    "prod-web-03":   "i-0a1b2c3d4e5f00003",
    "prod-app-01":   "i-0a1b2c3d4e5f00004",
    "prod-app-02":   "i-0a1b2c3d4e5f00005",
    "prod-db-01":    "i-0a1b2c3d4e5f00006",
    "prod-bastion":  "i-0a1b2c3d4e5f00007",
    "dev-build-01":  "i-0a1b2c3d4e5f00008",
    "dev-test-01":   "i-0a1b2c3d4e5f00009",
    "dev-test-02":   "i-0a1b2c3d4e5f00010",
    "prod-ml-worker":"i-0a1b2c3d4e5f00011",
    "prod-ecs-host": "i-0a1b2c3d4e5f00012",
}

def build_findings():
    findings = []

    # ── A. Security Hub findings (150) ───────────────────────────────────────
    sh_items = [
        # CIS + FSBP misconfigs
        ("critical", "S3 Bucket prod-data-lake Has Public Read Access",
         "The S3 bucket prod-data-lake has a public-read ACL, exposing all objects to the internet. This is a critical data exposure risk.",
         s3_arn("prod-data-lake"), "AWS::S3::Bucket",
         ["CIS 2.1.5", "PCI DSS 1.3", "NIST AC-3"],
         "Remove the public ACL: aws s3api put-bucket-acl --bucket prod-data-lake --acl private. Enable S3 Block Public Access.", 9.8),

        ("critical", "S3 Bucket prod-customer-pii Has No Server-Side Encryption",
         "prod-customer-pii stores customer PII without server-side encryption. Data at rest is unprotected.",
         s3_arn("prod-customer-pii"), "AWS::S3::Bucket",
         ["CIS 2.1.1", "HIPAA §164.312(a)(2)(iv)", "PCI DSS 3.4", "GDPR Article 32"],
         "Enable SSE-KMS: aws s3api put-bucket-encryption --bucket prod-customer-pii --server-side-encryption-configuration ...", 9.5),

        ("critical", "RDS Instance prod-mysql-01 Is Publicly Accessible",
         "The RDS MySQL instance prod-mysql-01 has PubliclyAccessible=true and is reachable from the internet. The security group allows 0.0.0.0/0 on port 3306.",
         rds_arn("prod-mysql-01"), "AWS::RDS::DBInstance",
         ["CIS 2.3.1", "PCI DSS 1.2", "NIST SC-7"],
         "Set PubliclyAccessible=false: aws rds modify-db-instance --db-instance-identifier prod-mysql-01 --no-publicly-accessible. Restrict SG rules.", 9.9),

        ("critical", "IAM User admin-user Has No MFA Enabled",
         "The IAM user admin-user has AdministratorAccess and no MFA device enrolled. Console and programmatic access are unprotected.",
         iam_user_arn("admin-user"), "AWS::IAM::User",
         ["CIS 1.10", "PCI DSS 8.3", "NIST IA-2"],
         "Enforce MFA: go to IAM console -> admin-user -> Security credentials -> Assign MFA device. Consider SCPs to deny without MFA.", 9.7),

        ("critical", "Lambda Function prod-payment-processor Contains Hardcoded API Key",
         "The Lambda function prod-payment-processor has a live Stripe API key hardcoded in an environment variable. This is a PCI DSS critical violation.",
         lambda_arn("prod-payment-processor"), "AWS::Lambda::Function",
         ["PCI DSS 6.3.1", "PCI DSS 8.2.1", "NIST IA-5"],
         "Remove hardcoded key immediately. Rotate the Stripe key. Store in Secrets Manager and reference via secretsmanager:GetSecretValue.", 10.0),

        ("critical", "Security Group sg-prod-db Allows Unrestricted MySQL Access from Internet",
         "Security group sg-prod-db has an inbound rule allowing 0.0.0.0/0 on port 3306, exposing MySQL to the entire internet.",
         sg_arn("sg-prod-db"), "AWS::EC2::SecurityGroup",
         ["CIS 5.2", "PCI DSS 1.2.1", "NIST SC-7"],
         "Remove the 0.0.0.0/0 rule: aws ec2 revoke-security-group-ingress --group-id sg-prod-db --protocol tcp --port 3306 --cidr 0.0.0.0/0", 9.8),

        ("critical", "Lambda Function prod-api-handler Has DB Password in Environment Variables",
         "prod-api-handler exposes a plaintext database password in the Lambda environment variable DB_PASSWORD.",
         lambda_arn("prod-api-handler"), "AWS::Lambda::Function",
         ["CIS 2.1.1", "PCI DSS 8.2.1", "NIST IA-5", "SOC2 CC6.1"],
         "Move DB_PASSWORD to AWS Secrets Manager. Update Lambda to call secretsmanager:GetSecretValue at runtime.", 9.6),

        ("critical", "IAM Role github-actions-role Missing OIDC Condition — Any GitHub Repo Can Assume It",
         "The github-actions-role has an OIDC trust policy without a Condition block. Any GitHub Actions workflow from any repository can assume this role and gain access to production AWS resources.",
         iam_role_arn("github-actions-role"), "AWS::IAM::Role",
         ["CIS 1.16", "NIST AC-6", "SOC2 CC6.3"],
         "Add Condition to trust policy: {\"StringLike\": {\"token.actions.githubusercontent.com:sub\": \"repo:YOUR_ORG/YOUR_REPO:*\"}}. Rotate all credentials immediately.", 10.0),

        ("high", "S3 Bucket prod-financial-reports Has Versioning Disabled",
         "prod-financial-reports stores financial reports without versioning. Accidental deletion or ransomware would result in permanent data loss.",
         s3_arn("prod-financial-reports"), "AWS::S3::Bucket",
         ["CIS 2.1.3", "SOC2 A1.2", "NIST CP-9"],
         "Enable versioning: aws s3api put-bucket-versioning --bucket prod-financial-reports --versioning-configuration Status=Enabled", 7.5),

        ("high", "S3 Bucket prod-app-logs Is Publicly Accessible",
         "prod-app-logs has public read access, exposing application logs that may contain sensitive information, internal IP addresses, and user activity patterns.",
         s3_arn("prod-app-logs"), "AWS::S3::Bucket",
         ["CIS 2.1.5", "PCI DSS 1.3"],
         "Apply Block Public Access settings and remove public ACL.", 8.1),

        ("high", "RDS Instance dev-mysql-01 Running Outdated MySQL 5.7",
         "dev-mysql-01 runs MySQL 5.7 which has reached end-of-life and contains known unpatched vulnerabilities.",
         rds_arn("dev-mysql-01"), "AWS::RDS::DBInstance",
         ["CIS 2.3.2", "PCI DSS 6.3.3", "NIST SI-2"],
         "Upgrade to MySQL 8.0: create a new DB instance with 8.0, use DMS to migrate data, update connection strings.", 8.2),

        ("high", "IAM User deploy-user Access Keys Not Rotated in 90+ Days",
         "deploy-user has access keys older than 90 days. Stale credentials increase the attack surface if they are compromised.",
         iam_user_arn("deploy-user"), "AWS::IAM::User",
         ["CIS 1.14", "PCI DSS 8.3.9", "NIST IA-5"],
         "Rotate access keys: aws iam create-access-key --user-name deploy-user. Deactivate old key. Update CI/CD secrets.", 7.8),

        ("high", "ECS Task Definition prod-privileged-task Has privileged=true",
         "The ECS task definition prod-privileged-task runs containers with privileged mode enabled, allowing container escape to the host EC2 instance.",
         f"arn:aws:ecs:us-east-1:{PROD_ACCOUNT_ID}:task-definition/prod-privileged-task:1", "AWS::ECS::TaskDefinition",
         ["CIS 5.3.2", "NIST CM-7", "SOC2 CC6.8"],
         "Set privileged: false in the task definition container definition. Use IAM task roles instead of host privileges.", 8.5),

        ("high", "SageMaker Execution Role Has iam:CreateRole and iam:AttachRolePolicy",
         "sagemaker-execution-role can create new IAM roles and attach policies — a privilege escalation path to AdministratorAccess.",
         iam_role_arn("sagemaker-execution-role"), "AWS::IAM::Role",
         ["CIS 1.16", "NIST AC-6", "PCI DSS 7.2"],
         "Remove iam:CreateRole and iam:AttachRolePolicy from the SageMaker role. Use permission boundaries.", 8.8),

        ("high", "CloudTrail prod-trail Is Not Multi-Region",
         "prod-trail only covers us-east-1. API activity in other regions is not logged, creating blind spots for security monitoring.",
         trail_arn("prod-trail"), "AWS::CloudTrail::Trail",
         ["CIS 3.1", "PCI DSS 10.2", "NIST AU-2"],
         "Update trail: aws cloudtrail update-trail --name prod-trail --is-multi-region-trail", 7.5),

        ("critical", "CloudTrail dev-trail Is Disabled",
         "The CloudTrail dev-trail is not logging. All API activity in the dev account is unmonitored. Attackers can operate without leaving traces.",
         trail_arn("dev-trail"), "AWS::CloudTrail::Trail",
         ["CIS 3.1", "PCI DSS 10.1", "HIPAA §164.312(b)"],
         "Enable logging: aws cloudtrail start-logging --name dev-trail", 9.3),

        ("high", "Security Group sg-prod-redis Allows Public Redis Access",
         "sg-prod-redis allows inbound traffic on port 6379 from 0.0.0.0/0, exposing Redis to the internet. Redis with no auth is trivially exploitable.",
         sg_arn("sg-prod-redis"), "AWS::EC2::SecurityGroup",
         ["CIS 5.2", "NIST SC-7"],
         "Restrict to VPC CIDR: aws ec2 revoke-security-group-ingress --group-id sg-prod-redis --protocol tcp --port 6379 --cidr 0.0.0.0/0", 9.2),

        ("critical", "Security Group sg-prod-elasticsearch Exposes Port 9200 to Internet",
         "Elasticsearch port 9200 is open to 0.0.0.0/0. Unauthenticated Elasticsearch clusters have been involved in numerous large data breaches.",
         sg_arn("sg-prod-elasticsearch"), "AWS::EC2::SecurityGroup",
         ["CIS 5.2", "PCI DSS 1.2", "NIST SC-7"],
         "Immediately revoke the 0.0.0.0/0 rule. Restrict to application tier security group only.", 9.5),

        ("critical", "Security Group sg-prod-ml Exposes Jupyter Notebook Port 8888",
         "Port 8888 (Jupyter Notebook) is publicly accessible from 0.0.0.0/0. A compromised Jupyter instance gives full code execution access.",
         sg_arn("sg-prod-ml"), "AWS::EC2::SecurityGroup",
         ["CIS 5.2", "NIST CM-7"],
         "Restrict sg-prod-ml port 8888 to VPN CIDR or known IP ranges only.", 9.4),

        ("high", "Security Group sg-dev-open Allows All Traffic from Internet",
         "sg-dev-open has a rule allowing all traffic (-1 protocol) from 0.0.0.0/0, exposing all instances in the dev environment.",
         sg_arn("sg-dev-open"), "AWS::EC2::SecurityGroup",
         ["CIS 5.2", "PCI DSS 1.2", "NIST SC-7"],
         "Delete the all-traffic rule. Create specific rules for required services only.", 8.9),

        ("high", "RDS prod-mysql-01 Has No Encryption at Rest",
         "prod-mysql-01 does not have storage encryption enabled. Customer data stored in this database is unprotected if storage media is compromised.",
         rds_arn("prod-mysql-01"), "AWS::RDS::DBInstance",
         ["CIS 2.3.1", "PCI DSS 3.5", "HIPAA §164.312(a)(2)(iv)"],
         "Create encrypted snapshot and restore to new encrypted instance. Enable KMS encryption.", 8.3),

        ("high", "VPC Flow Logs Disabled on prod-vpc",
         "prod-vpc does not have VPC Flow Logs enabled. Network traffic visibility is absent, hampering incident response.",
         f"arn:aws:ec2:us-east-1:{PROD_ACCOUNT_ID}:vpc/vpc-prod", "AWS::EC2::VPC",
         ["CIS 3.9", "PCI DSS 10.3", "NIST AU-12"],
         "Enable flow logs: aws ec2 create-flow-logs --resource-type VPC --resource-ids vpc-prod --traffic-type ALL --log-group-name /aws/vpc/flowlogs", 7.8),

        ("high", "KMS Key prod-cmk-overpermissive Has Principal *",
         "The KMS CMK prod-cmk-overpermissive has a key policy with Principal: '*', allowing any AWS principal to use the key.",
         f"arn:aws:kms:us-east-1:{PROD_ACCOUNT_ID}:key/prod-cmk-overpermissive", "AWS::KMS::Key",
         ["CIS 2.8", "PCI DSS 3.7", "NIST SC-12"],
         "Update key policy to restrict Principal to specific IAM roles/users. Remove wildcard principal.", 8.1),

        ("medium", "Lambda Function prod-api-handler Running Python 3.8 (End-of-Life)",
         "Python 3.8 reached end-of-life in October 2024. Lambda functions on deprecated runtimes may not receive security patches.",
         lambda_arn("prod-api-handler"), "AWS::Lambda::Function",
         ["CIS 2.1.1", "PCI DSS 6.3.3", "NIST SI-2"],
         "Upgrade runtime to Python 3.12. Test function compatibility and deploy.", 6.5),

        ("medium", "Lambda Function prod-data-processor Running Node.js 14 (End-of-Life)",
         "Node.js 14 is end-of-life. This Lambda function is not receiving security patches.",
         lambda_arn("prod-data-processor"), "AWS::Lambda::Function",
         ["PCI DSS 6.3.3", "NIST SI-2"],
         "Upgrade to Node.js 20. Update package.json dependencies and test.", 6.2),

        ("medium", "S3 Bucket prod-terraform-state Bucket Policy Too Permissive",
         "The Terraform state bucket has a bucket policy granting access to the entire AWS account. Terraform state can contain sensitive resource configurations and secrets.",
         s3_arn("prod-terraform-state"), "AWS::S3::Bucket",
         ["CIS 2.1.5", "SOC2 CC6.1"],
         "Restrict bucket policy to specific IAM roles that require Terraform access. Enable S3 access logging.", 7.1),

        ("medium", "CloudTrail prod-trail Log File Validation Disabled",
         "Log file validation ensures CloudTrail log integrity. Without it, logs could be tampered with undetected.",
         trail_arn("prod-trail"), "AWS::CloudTrail::Trail",
         ["CIS 3.2", "PCI DSS 10.5", "NIST AU-9"],
         "Enable log file validation: aws cloudtrail update-trail --name prod-trail --enable-log-file-validation", 6.8),

        ("medium", "RDS prod-mysql-01 Has Multi-AZ Disabled",
         "prod-mysql-01 is a single-AZ deployment. An AZ failure would cause unplanned downtime with potential data loss.",
         rds_arn("prod-mysql-01"), "AWS::RDS::DBInstance",
         ["SOC2 A1.1", "NIST CP-6"],
         "Enable Multi-AZ: aws rds modify-db-instance --db-instance-identifier prod-mysql-01 --multi-az --apply-immediately", 5.5),

        ("high", "IAM Role prod-ec2-instance-role Has s3:* and iam:PassRole",
         "prod-ec2-instance-role grants all S3 actions and iam:PassRole to EC2 instances. This enables data exfiltration and privilege escalation.",
         iam_role_arn("prod-ec2-instance-role"), "AWS::IAM::Role",
         ["CIS 1.16", "NIST AC-6", "PCI DSS 7.2"],
         "Apply least privilege. Remove s3:* and replace with specific bucket/action permissions. Remove iam:PassRole unless required.", 8.9),

        ("high", "Lambda prod-image-resizer Has Public Function URL With No Auth",
         "prod-image-resizer has a public Lambda Function URL with AuthType=NONE. Anyone can invoke this function without authentication.",
         lambda_arn("prod-image-resizer"), "AWS::Lambda::Function",
         ["CIS 2.1.1", "NIST AC-3", "SOC2 CC6.2"],
         "Update function URL auth type to AWS_IAM: aws lambda update-function-url-config --function-name prod-image-resizer --auth-type AWS_IAM", 7.8),

        ("medium", "S3 Bucket prod-database-backups Has No Lifecycle Policy",
         "Database backups accumulate indefinitely without a lifecycle policy, increasing storage costs and the blast radius of a data breach.",
         s3_arn("prod-database-backups"), "AWS::S3::Bucket",
         ["SOC2 A1.2", "NIST CP-9"],
         "Create lifecycle rule to transition to Glacier after 30 days and expire after 365 days.", 5.2),

        ("medium", "EC2 Instance prod-bastion Allows SSH from 0.0.0.0/0",
         "The bastion host prod-bastion allows SSH (port 22) from any IP address. Brute force and credential stuffing attacks are possible.",
         ec2_arn(EC2_IDS["prod-bastion"]), "AWS::EC2::Instance",
         ["CIS 5.2", "PCI DSS 1.2", "NIST SC-7"],
         "Restrict SSH source to corporate VPN CIDR. Consider AWS Systems Manager Session Manager as a bastion replacement.", 7.2),

        ("informational", "S3 Bucket prod-media-assets MFA Delete Not Enabled",
         "MFA Delete is not enabled on prod-media-assets. Without MFA Delete, bucket contents can be permanently deleted without additional verification.",
         s3_arn("prod-media-assets"), "AWS::S3::Bucket",
         ["CIS 2.1.3"],
         "Enable MFA Delete on the bucket. Requires root account credentials.", 3.5),

        ("informational", "EC2 Instances Not Using Instance Metadata Service v2",
         "Multiple EC2 instances are using IMDSv1 which is susceptible to SSRF attacks. IMDSv2 should be enforced.",
         ec2_arn(EC2_IDS["prod-web-01"]), "AWS::EC2::Instance",
         ["CIS 5.7", "NIST CM-7"],
         "Enforce IMDSv2: aws ec2 modify-instance-metadata-options --instance-id i-xxx --http-tokens required --http-endpoint enabled", 4.5),
    ]

    # Pad out to 150 Security Hub findings
    extra_sh = [
        ("medium", f"S3 Bucket prod-backups Cross-Account Access Policy Too Broad",
         "prod-backups grants cross-account access without resource-level restrictions.", s3_arn("prod-backups"), "AWS::S3::Bucket",
         ["CIS 2.1.5", "NIST AC-3"], "Restrict cross-account policy to specific principals and S3 prefixes.", 6.8),
        ("medium", "EC2 prod-web-01 Using Default Security Group",
         "prod-web-01 is associated with the default VPC security group which should not be used.", ec2_arn(EC2_IDS["prod-web-01"]), "AWS::EC2::Instance",
         ["CIS 5.4"], "Remove instances from default security group. Use custom security groups.", 5.0),
        ("medium", "IAM Password Policy Does Not Require Uppercase Characters",
         "The account IAM password policy does not enforce uppercase characters.", f"arn:aws:iam::{PROD_ACCOUNT_ID}:root", "AWS::IAM::PasswordPolicy",
         ["CIS 1.8", "PCI DSS 8.3.6"], "Update password policy: minimum length 14, require uppercase, lowercase, numbers, symbols.", 5.5),
        ("medium", "IAM Password Policy Does Not Prevent Password Reuse",
         "Password policy does not prevent reuse of the last 24 passwords.", f"arn:aws:iam::{PROD_ACCOUNT_ID}:root", "AWS::IAM::PasswordPolicy",
         ["CIS 1.9", "PCI DSS 8.3.7"], "Set password reuse prevention to 24 in the IAM password policy.", 5.2),
        ("high", "Root Account Access Key Exists",
         "An active access key exists for the root account. Root access keys provide unrestricted access.", f"arn:aws:iam::{PROD_ACCOUNT_ID}:root", "AWS::IAM::User",
         ["CIS 1.4", "PCI DSS 8.2.1", "NIST IA-2"], "Delete the root access key immediately. Use IAM users/roles for all programmatic access.", 9.1),
        ("critical", "Root Account Has No MFA",
         "The AWS root account does not have MFA enabled.", f"arn:aws:iam::{PROD_ACCOUNT_ID}:root", "AWS::IAM::User",
         ["CIS 1.5", "PCI DSS 8.3.1"], "Enable MFA on root account immediately. Use hardware MFA token.", 9.5),
        ("medium", "No CloudWatch Alarm for Root Account Login",
         "There is no CloudWatch metric filter and alarm for root account login events.", f"arn:aws:cloudwatch:us-east-1:{PROD_ACCOUNT_ID}:alarm", "AWS::CloudWatch::Alarm",
         ["CIS 4.3", "PCI DSS 10.6"], "Create metric filter on CloudTrail logs for root login events and configure SNS alarm.", 6.5),
        ("medium", "No CloudWatch Alarm for Unauthorized API Calls",
         "No alarm configured for unauthorized API call events.", f"arn:aws:cloudwatch:us-east-1:{PROD_ACCOUNT_ID}:alarm", "AWS::CloudWatch::Alarm",
         ["CIS 4.1", "PCI DSS 10.6"], "Create CloudWatch alarm for AccessDenied and UnauthorizedOperation events.", 6.2),
        ("medium", "No CloudWatch Alarm for Console Login Without MFA",
         "No alarm for ConsoleLogin without MFA events in CloudTrail.", f"arn:aws:cloudwatch:us-east-1:{PROD_ACCOUNT_ID}:alarm", "AWS::CloudWatch::Alarm",
         ["CIS 4.2", "PCI DSS 8.3"], "Create metric filter for ConsoleLogin where additionalEventData.MFAUsed = No.", 6.8),
        ("high", "IAM Role prod-deploy-role Has AdministratorAccess and Is Assumed by CI/CD",
         "prod-deploy-role has AdministratorAccess and can be assumed by the CI/CD user. Any CI/CD pipeline compromise leads to full account takeover.",
         iam_role_arn("prod-deploy-role"), "AWS::IAM::Role",
         ["CIS 1.16", "NIST AC-6", "PCI DSS 7.2"], "Restrict prod-deploy-role to only the permissions needed for deployment. Use permission boundaries.", 8.7),
        ("medium", "S3 Bucket dev-build-artifacts Is Publicly Readable",
         "Build artifacts may contain sensitive configuration, internal URLs, or compiled code.", s3_arn("dev-build-artifacts"), "AWS::S3::Bucket",
         ["CIS 2.1.5"], "Enable S3 Block Public Access on dev-build-artifacts.", 6.5),
        ("medium", "S3 Bucket prod-cf-templates Is Public",
         "CloudFormation templates may expose infrastructure design and resource configurations.", s3_arn("prod-cf-templates"), "AWS::S3::Bucket",
         ["CIS 2.1.5"], "Remove public access from prod-cf-templates.", 6.8),
        ("low", "Lambda prod-etl-job Has Overly Broad s3:* Permission",
         "prod-etl-job only needs to read specific S3 buckets but has s3:* on all resources.", lambda_arn("prod-etl-job"), "AWS::Lambda::Function",
         ["NIST AC-6", "CIS 1.16"], "Scope Lambda IAM role to specific buckets and actions required.", 5.5),
        ("medium", "dev-test-function Has Admin IAM Role Attached",
         "A Lambda function in dev has an admin IAM role. If exploited, full account access is possible.", lambda_arn("dev-test-function"), "AWS::Lambda::Function",
         ["CIS 1.16", "NIST AC-6"], "Replace admin role with least-privilege role scoped to dev resources only.", 7.5),
        ("high", "RDS dev-mysql-01 Is Publicly Accessible With No Auth Requirements",
         "dev-mysql-01 (MySQL 5.7) is publicly accessible. Combined with outdated version, high exploitation risk.", rds_arn("dev-mysql-01"), "AWS::RDS::DBInstance",
         ["CIS 2.3.1", "PCI DSS 1.2"], "Disable public accessibility immediately. Restrict to private subnet.", 8.5),
    ]

    # Merge and create finding records
    all_sh = sh_items + extra_sh

    # Generate to 150 total
    generic_sh_titles = [
        ("low", "S3 Bucket Access Logging Disabled", s3_arn("prod-ml-training-data"), "AWS::S3::Bucket", ["CIS 2.1.4"], 4.0),
        ("low", "EC2 Instance prod-app-01 Not Using Latest Generation Instance Type", ec2_arn(EC2_IDS["prod-app-01"]), "AWS::EC2::Instance", ["NIST CM-2"], 3.5),
        ("medium", "ECS Cluster prod-ecs-cluster Container Insights Disabled", f"arn:aws:ecs:us-east-1:{PROD_ACCOUNT_ID}:cluster/prod-ecs-cluster", "AWS::ECS::Cluster", ["NIST AU-12"], 5.0),
        ("low", "Lambda prod-auth-service Not Configured with Dead Letter Queue", lambda_arn("prod-auth-service"), "AWS::Lambda::Function", ["SOC2 A1.2"], 3.2),
        ("medium", "RDS prod-postgres-01 Minor Version Upgrade Not Enabled", rds_arn("prod-postgres-01"), "AWS::RDS::DBInstance", ["PCI DSS 6.3.3"], 5.5),
        ("low", "S3 Bucket dev-ml-experiments Cross-Region Replication Not Configured", s3_arn("dev-ml-experiments"), "AWS::S3::Bucket", ["SOC2 A1.2"], 3.0),
        ("medium", "IAM User ci-cd-user Console Access Not Disabled", iam_user_arn("ci-cd-user"), "AWS::IAM::User", ["CIS 1.15"], 5.8),
        ("low", "EC2 prod-bastion No Termination Protection", ec2_arn(EC2_IDS["prod-bastion"]), "AWS::EC2::Instance", ["SOC2 A1.1"], 3.5),
        ("medium", "CloudWatch Log Group /aws/lambda/prod-api-handler Not Encrypted", f"arn:aws:logs:us-east-1:{PROD_ACCOUNT_ID}:log-group:/aws/lambda/prod-api-handler", "AWS::Logs::LogGroup", ["CIS 2.1.1"], 6.0),
        ("low", "RDS prod-mysql-01 Automated Backups Retention Less Than 7 Days", rds_arn("prod-mysql-01"), "AWS::RDS::DBInstance", ["SOC2 A1.2"], 4.5),
        ("informational", "S3 Bucket prod-static-assets No Intelligent Tiering", s3_arn("prod-static-assets"), "AWS::S3::Bucket", ["NIST CP-9"], 2.5),
        ("medium", "IAM User ml-engineer-user Has iam:PassRole with SageMaker", iam_user_arn("ml-engineer-user"), "AWS::IAM::User", ["CIS 1.16", "NIST AC-6"], 7.0),
        ("low", "EC2 prod-web-01 No Detailed Monitoring Enabled", ec2_arn(EC2_IDS["prod-web-01"]), "AWS::EC2::Instance", ["NIST AU-12"], 3.0),
        ("medium", "Lambda prod-ml-inference Public Internet-Facing Endpoint", lambda_arn("prod-ml-inference"), "AWS::Lambda::Function", ["NIST SC-7"], 6.5),
        ("low", "KMS Key prod-cmk-s3 Rotation Not Enabled", f"arn:aws:kms:us-east-1:{PROD_ACCOUNT_ID}:key/prod-cmk-s3", "AWS::KMS::Key", ["CIS 2.8", "PCI DSS 3.7"], 5.0),
    ]

    # Build all_sh up to 150
    for sev_g, title_g, arn_g, rtype_g, fw_g, score_g in generic_sh_titles:
        all_sh.append((
            sev_g,
            title_g,
            f"AWS Security Hub FSBP finding: {title_g}",
            arn_g, rtype_g, fw_g,
            f"Review and remediate the finding for {arn_g}.", score_g
        ))

    # Pad remaining to 150
    filler_resources = [
        (s3_arn("prod-data-lake"), "AWS::S3::Bucket"),
        (ec2_arn(EC2_IDS["prod-web-01"]), "AWS::EC2::Instance"),
        (iam_user_arn("dev-user-1"), "AWS::IAM::User"),
        (rds_arn("prod-mysql-01"), "AWS::RDS::DBInstance"),
        (lambda_arn("prod-api-handler"), "AWS::Lambda::Function"),
    ]
    severities = ["low", "informational", "medium", "low", "informational"]
    while len(all_sh) < 150:
        i = len(all_sh) % len(filler_resources)
        res_arn, res_type = filler_resources[i]
        all_sh.append((
            severities[i],
            f"AWS Foundational Security Best Practice Violation #{len(all_sh)+1}",
            f"Security Hub FSBP finding #{len(all_sh)+1} — resource does not meet AWS security standard requirements.",
            res_arn, res_type, ["CIS 2.1.1"],
            "Review the resource configuration against AWS Security Best Practices.", 3.5
        ))

    regions = ["us-east-1", "us-east-1", "us-east-1", "us-west-2", "eu-west-1"]
    acct_ids = [PROD_ACCOUNT_UUID, PROD_ACCOUNT_UUID, PROD_ACCOUNT_UUID, DEV_ACCOUNT_UUID, SEC_ACCOUNT_UUID]
    aws_acct_nos = [PROD_ACCOUNT_ID, PROD_ACCOUNT_ID, PROD_ACCOUNT_ID, DEV_ACCOUNT_ID, SEC_ACCOUNT_ID]

    for idx, item in enumerate(all_sh[:150]):
        sev, title, desc, res_arn, res_type, fw, remediation, risk = item
        fid = uid()
        ri = idx % len(regions)
        findings.append({
            "id": strip(fid),
            "workspace_id": strip(WORKSPACE_ID),
            "aws_account_id": strip(acct_ids[ri]),
            "fingerprint": f"sh-{idx:04d}-" + fid[:8],
            "primary_source": "security_hub",
            "severity": sev,
            "status": random.choice(["open", "open", "open", "in_progress"]),
            "risk_score": risk,
            "title": title,
            "description": desc,
            "remediation": remediation,
            "resource_arn": res_arn,
            "resource_type": res_type,
            "region": regions[ri],
            "compliance_frameworks": json.dumps(fw),
            "tags": json.dumps({"account": aws_acct_nos[ri], "source": "security_hub"}),
            "first_seen_at": days_ago(random.randint(1, 180)),
            "last_seen_at": days_ago(random.randint(0, 7)),
            "resolved_at": None,
            "created_at": days_ago(random.randint(1, 180)),
            "updated_at": days_ago(random.randint(0, 7)),
        })

    # ── B. GuardDuty findings (100) ──────────────────────────────────────────
    gd_items = [
        ("critical", "UnauthorizedAccess:IAMUser/TorIPCaller",
         "An API call was made from an IP address on the Tor network by IAM user dev-user-1. This may indicate compromised credentials being used anonymously.",
         iam_user_arn("dev-user-1"), "AWS::IAM::User", 9.2,
         "Disable IAM user dev-user-1 immediately. Rotate all credentials. Review CloudTrail for unauthorized actions.", ["PCI DSS 10.6", "NIST IR-4"]),
        ("critical", "Backdoor:EC2/C&CActivity.B",
         "EC2 instance prod-web-01 is communicating with a known command-and-control server. The instance may be compromised.",
         ec2_arn(EC2_IDS["prod-web-01"]), "AWS::EC2::Instance", 9.5,
         "Isolate instance immediately. Create forensic snapshot. Terminate and replace. Investigate lateral movement.", ["PCI DSS 11.5", "NIST IR-4"]),
        ("critical", "CryptoCurrency:EC2/BitcoinTool.B",
         "EC2 instance dev-test-01 is querying Bitcoin-related domains. The instance may be used for unauthorized cryptocurrency mining.",
         ec2_arn(EC2_IDS["dev-test-01"]), "AWS::EC2::Instance", 8.8,
         "Terminate the instance. Review IAM permissions used. Scan other instances for similar activity.", ["NIST IR-5"]),
        ("critical", "Trojan:EC2/BlackholeTraffic",
         "EC2 instance prod-app-01 is attempting to communicate with a known blackhole domain. Possible malware infection.",
         ec2_arn(EC2_IDS["prod-app-01"]), "AWS::EC2::Instance", 9.1,
         "Isolate instance. Perform malware analysis. Replace instance from clean AMI.", ["NIST IR-4"]),
        ("high", "Recon:IAMUser/MaliciousIPCaller",
         "Reconnaissance API calls (DescribeInstances, ListBuckets) made from a known malicious IP address associated with IAM user ci-cd-user.",
         iam_user_arn("ci-cd-user"), "AWS::IAM::User", 8.3,
         "Review all API calls from this IP. Disable ci-cd-user if unauthorized. Rotate access keys.", ["PCI DSS 11.4", "NIST CA-7"]),
        ("high", "UnauthorizedAccess:EC2/SSHBruteForce",
         "prod-bastion is experiencing SSH brute force attack from IP 185.220.101.45. Multiple failed login attempts detected.",
         ec2_arn(EC2_IDS["prod-bastion"]), "AWS::EC2::Instance", 7.8,
         "Block the attacking IP in security group. Enable fail2ban. Consider moving to SSM Session Manager.", ["CIS 5.2", "NIST SC-7"]),
        ("high", "Stealth:IAMUser/PasswordPolicyChange",
         "The IAM password policy was modified by dev-user-2 from an unusual IP. This may indicate an attempt to weaken security controls.",
         iam_user_arn("dev-user-2"), "AWS::IAM::User", 7.5,
         "Revert password policy changes. Review who has permission to modify password policy. Alert security team.", ["CIS 1.8", "PCI DSS 8.3"]),
        ("high", "UnauthorizedAccess:IAMUser/ConsoleLoginSuccess.B",
         "Successful console login from unusual geographic location (Romania) for admin-user who normally accesses from US.",
         iam_user_arn("admin-user"), "AWS::IAM::User", 8.5,
         "Verify with user if login was authorized. If not, disable account, rotate credentials, review all actions taken.", ["PCI DSS 10.6", "NIST IR-4"]),
        ("high", "Impact:EC2/PortSweep",
         "EC2 instance dev-build-01 is performing a port sweep across internal subnets. Possible insider threat or compromised instance.",
         ec2_arn(EC2_IDS["dev-build-01"]), "AWS::EC2::Instance", 7.9,
         "Isolate dev-build-01. Review network flow logs. Investigate who has access to this instance.", ["NIST SI-3"]),
        ("high", "Exfiltration:S3/ObjectRead.Unusual",
         "Unusually high volume of S3 GetObject calls on prod-customer-pii from IP 203.0.113.50. Possible data exfiltration.",
         s3_arn("prod-customer-pii"), "AWS::S3::Bucket", 9.0,
         "Block the source IP. Review S3 access logs. Assess what data was accessed. Notify legal/compliance.", ["PCI DSS 10.3", "HIPAA §164.312(b)"]),
        ("medium", "Discovery:S3/BucketEnumeration.Unusual",
         "IAM entity dev-user-3 made ListBuckets calls from an unusual IP, enumerating all S3 buckets in the account.",
         iam_user_arn("dev-user-3"), "AWS::IAM::User", 6.5,
         "Review S3 bucket enumeration. Check if dev-user-3 credentials were compromised. Restrict ListBuckets permission.", ["NIST CA-7"]),
        ("medium", "Persistence:IAMUser/UserPermissions",
         "IAM user dev-user-4 created a new IAM user with administrative permissions outside of normal business hours.",
         iam_user_arn("dev-user-4"), "AWS::IAM::User", 7.2,
         "Review new IAM users created. Disable unauthorized accounts. Alert on iam:CreateUser events.", ["CIS 1.16", "NIST AC-2"]),
        ("medium", "Trojan:Lambda/BlackholeTraffic",
         "Lambda function prod-data-processor is making DNS queries to known malicious domains. Package may contain malicious code.",
         lambda_arn("prod-data-processor"), "AWS::Lambda::Function", 7.0,
         "Review Lambda function code and dependencies. Check for malicious npm packages. Rebuild from trusted base.", ["NIST SI-3"]),
        ("high", "UnauthorizedAccess:IAMUser/InstanceCredentialExfiltration.OutsideAWS",
         "Credentials from EC2 instance prod-ml-worker were used from an IP address outside AWS. Possible SSRF-based credential theft.",
         ec2_arn(EC2_IDS["prod-ml-worker"]), "AWS::EC2::Instance", 8.7,
         "Rotate instance credentials via IAM. Review the SSRF vulnerability. Enable IMDSv2. Isolate instance.", ["NIST IR-4"]),
        ("medium", "Policy:S3/BucketBlockPublicAccessDisabled",
         "S3 Block Public Access was disabled on prod-data-lake. This change was made via console from IP 192.168.1.100.",
         s3_arn("prod-data-lake"), "AWS::S3::Bucket", 7.5,
         "Re-enable Block Public Access. Review who made this change and whether it was authorized.", ["CIS 2.1.5"]),
    ]

    # Fill to 100 GuardDuty
    gd_extra_templates = [
        ("medium", "Recon:EC2/PortProbeUnprotectedPort", ec2_arn(EC2_IDS["prod-web-02"]), "AWS::EC2::Instance", 6.0),
        ("medium", "Recon:EC2/Portscan", ec2_arn(EC2_IDS["prod-web-03"]), "AWS::EC2::Instance", 6.5),
        ("high", "UnauthorizedAccess:EC2/RDPBruteForce", ec2_arn(EC2_IDS["prod-web-01"]), "AWS::EC2::Instance", 7.5),
        ("medium", "Discovery:IAMUser/AnomalousBehavior", iam_user_arn("data-analyst-user"), "AWS::IAM::User", 6.2),
        ("high", "Impact:S3/PermissionsModification.Unusual", s3_arn("prod-financial-reports"), "AWS::S3::Bucket", 8.0),
        ("medium", "DefenseEvasion:IAMUser/AnomalousBehavior", iam_user_arn("deploy-user"), "AWS::IAM::User", 7.0),
        ("high", "Execution:Lambda/SuspiciousNetwork", lambda_arn("prod-api-handler"), "AWS::Lambda::Function", 7.8),
        ("medium", "Discovery:RDS/MaliciousIPCaller", rds_arn("prod-mysql-01"), "AWS::RDS::DBInstance", 6.5),
        ("high", "CredentialAccess:IAMUser/AnomalousBehavior", iam_user_arn("admin-user"), "AWS::IAM::User", 8.2),
        ("medium", "Impact:EC2/DenialOfService.Tcp", ec2_arn(EC2_IDS["prod-ecs-host"]), "AWS::EC2::Instance", 7.0),
    ]

    for sev, title, res_arn, res_type, risk in gd_extra_templates:
        gd_items.append((
            sev, title,
            f"GuardDuty threat intelligence finding: {title}. Suspicious activity detected requiring immediate investigation.",
            res_arn, res_type, risk,
            f"Investigate {res_arn} for {title}. Review CloudTrail. Engage incident response if confirmed.",
            ["NIST IR-4", "PCI DSS 11.4"]
        ))

    while len(gd_items) < 100:
        i = len(gd_items) % len(gd_extra_templates)
        sev, title, res_arn, res_type, risk = gd_extra_templates[i]
        gd_items.append((
            random.choice(["medium", "low"]),
            f"GuardDuty Finding: Suspicious Activity #{len(gd_items)+1}",
            f"GuardDuty detected suspicious activity pattern #{len(gd_items)+1} requiring review.",
            res_arn, res_type, risk * 0.7,
            "Review CloudTrail and network flow logs for the affected resource.",
            ["NIST CA-7"]
        ))

    gd_regions = ["us-east-1", "us-west-2", "eu-west-1"]
    gd_accts = [PROD_ACCOUNT_UUID, DEV_ACCOUNT_UUID, PROD_ACCOUNT_UUID]
    for idx, item in enumerate(gd_items[:100]):
        sev, title, desc, res_arn, res_type, risk, remediation, fw = item
        fid = uid()
        ri = idx % len(gd_regions)
        findings.append({
            "id": strip(fid),
            "workspace_id": strip(WORKSPACE_ID),
            "aws_account_id": strip(gd_accts[ri]),
            "fingerprint": f"gd-{idx:04d}-" + fid[:8],
            "primary_source": "guard_duty",
            "severity": sev,
            "status": random.choice(["open", "open", "in_progress"]),
            "risk_score": min(risk, 10.0),
            "title": title,
            "description": desc,
            "remediation": remediation,
            "resource_arn": res_arn,
            "resource_type": res_type,
            "region": gd_regions[ri],
            "compliance_frameworks": json.dumps(fw),
            "tags": json.dumps({"source": "guard_duty", "detector": "gd-prod-01"}),
            "first_seen_at": days_ago(random.randint(1, 60)),
            "last_seen_at": days_ago(random.randint(0, 3)),
            "resolved_at": None,
            "created_at": days_ago(random.randint(1, 60)),
            "updated_at": days_ago(random.randint(0, 3)),
        })

    # ── C. Inspector findings (100) ──────────────────────────────────────────
    inspector_items = [
        ("critical", "CVE-2021-44228 Log4Shell in prod-web-01",
         "Critical Log4Shell vulnerability (CVE-2021-44228) detected in log4j-core 2.14.1 on prod-web-01. CVSS 10.0. CISA KEV listed. Active exploitation in the wild. Allows remote code execution via JNDI injection.",
         ec2_arn(EC2_IDS["prod-web-01"]), "AWS::EC2::Instance", 10.0, ["PCI DSS 6.3.3", "NIST SI-2", "CIS 7.1"]),
        ("critical", "CVE-2022-22965 Spring4Shell in prod-web-02",
         "Spring4Shell (CVE-2022-22965) affects spring-webmvc on prod-web-02. CVSS 9.8. Allows unauthenticated RCE via data binding.",
         ec2_arn(EC2_IDS["prod-web-02"]), "AWS::EC2::Instance", 9.8, ["PCI DSS 6.3.3", "NIST SI-2"]),
        ("critical", "CVE-2023-44487 HTTP/2 Rapid Reset in prod-web-03",
         "HTTP/2 Rapid Reset Attack (CVE-2023-44487) vulnerability on prod-web-03. CISA KEV listed. DDoS amplification vector.",
         ec2_arn(EC2_IDS["prod-web-03"]), "AWS::EC2::Instance", 7.5, ["NIST SI-2", "PCI DSS 6.3.3"]),
        ("critical", "CVE-2021-45046 Log4j2 JNDI Thread Context in prod-app-01",
         "Secondary Log4Shell bypass (CVE-2021-45046) on prod-app-01 in log4j-core 2.15.0. CVSS 9.0. RCE via context lookup.",
         ec2_arn(EC2_IDS["prod-app-01"]), "AWS::EC2::Instance", 9.0, ["PCI DSS 6.3.3", "NIST SI-2"]),
        ("high", "CVE-2022-3602 OpenSSL Buffer Overflow in prod-bastion",
         "OpenSSL 3.0.x buffer overflow (CVE-2022-3602) on prod-bastion. Potential code execution during TLS handshake.",
         ec2_arn(EC2_IDS["prod-bastion"]), "AWS::EC2::Instance", 7.8, ["PCI DSS 6.3.3"]),
        ("high", "CVE-2023-23397 Microsoft Exchange in prod-app-02",
         "CVE-2023-23397 NTLM credential relay vulnerability detected. CISA KEV listed.",
         ec2_arn(EC2_IDS["prod-app-02"]), "AWS::EC2::Instance", 8.8, ["NIST SI-2"]),
        ("critical", "CVE-2021-44228 Log4Shell in lambda prod-api-handler",
         "Log4j-core 2.14.1 embedded in Lambda deployment package for prod-api-handler. CVSS 10.0.",
         lambda_arn("prod-api-handler"), "AWS::Lambda::Function", 10.0, ["PCI DSS 6.3.3", "NIST SI-2"]),
        ("high", "CVE-2022-42889 Apache Commons Text in prod-data-processor",
         "Apache Commons Text StringSubstitutor RCE (CVE-2022-42889) — Text4Shell. Embedded in Lambda deployment package.",
         lambda_arn("prod-data-processor"), "AWS::Lambda::Function", 9.0, ["PCI DSS 6.3.3"]),
        ("high", "CVE-2022-22963 Spring Cloud Function RCE in prod-etl-job",
         "Spring Cloud Function routing expression injection (CVE-2022-22963) in prod-etl-job Lambda. CVSS 9.8.",
         lambda_arn("prod-etl-job"), "AWS::Lambda::Function", 9.8, ["PCI DSS 6.3.3"]),
        ("critical", "CVE-2021-44228 Log4Shell in prod-ml-worker",
         "Log4Shell in log4j-core detected on ML worker instance prod-ml-worker running Spark workloads.",
         ec2_arn(EC2_IDS["prod-ml-worker"]), "AWS::EC2::Instance", 10.0, ["NIST SI-2"]),
        ("high", "CVE-2023-35708 MOVEit SQL Injection in prod-ecs-host",
         "MOVEit Transfer SQL injection (CVE-2023-35708) detected. CISA KEV listed.",
         ec2_arn(EC2_IDS["prod-ecs-host"]), "AWS::EC2::Instance", 9.0, ["NIST SI-2", "PCI DSS 6.3.3"]),
        ("high", "CVE-2022-26134 Confluence RCE in dev-build-01",
         "Atlassian Confluence OGNL injection (CVE-2022-26134) on dev-build-01. CVSS 9.8. CISA KEV.",
         ec2_arn(EC2_IDS["dev-build-01"]), "AWS::EC2::Instance", 9.8, ["PCI DSS 6.3.3"]),
        ("high", "CVE-2023-22515 Confluence Broken Access Control in dev-test-01",
         "Atlassian Confluence broken access control (CVE-2023-22515). Allows creation of admin accounts.",
         ec2_arn(EC2_IDS["dev-test-01"]), "AWS::EC2::Instance", 9.8, ["NIST SI-2"]),
        ("medium", "CVE-2022-40684 FortiOS Auth Bypass in dev-test-02",
         "Fortinet FortiOS authentication bypass (CVE-2022-40684). CISA KEV listed.",
         ec2_arn(EC2_IDS["dev-test-02"]), "AWS::EC2::Instance", 9.8, ["NIST SI-2"]),
        ("medium", "CVE-2023-20198 Cisco IOS XE in prod-db-01",
         "Cisco IOS XE web UI privilege escalation (CVE-2023-20198). CISA KEV.",
         ec2_arn(EC2_IDS["prod-db-01"]), "AWS::EC2::Instance", 10.0, ["NIST SI-2"]),
    ]

    # Pad Inspector to 100
    inspector_extra = [
        ("medium", "CVE-2021-3177 Python Buffer Overflow", lambda_arn("prod-auth-service"), "AWS::Lambda::Function", 6.5),
        ("medium", "CVE-2022-0778 OpenSSL Infinite Loop", ec2_arn(EC2_IDS["prod-web-01"]), "AWS::EC2::Instance", 7.5),
        ("high", "CVE-2021-41773 Apache Path Traversal", ec2_arn(EC2_IDS["prod-web-02"]), "AWS::EC2::Instance", 7.4),
        ("high", "CVE-2021-42013 Apache RCE", ec2_arn(EC2_IDS["prod-web-03"]), "AWS::EC2::Instance", 9.8),
        ("medium", "CVE-2022-21449 Java ECDSA Signature Bypass", lambda_arn("prod-payment-processor"), "AWS::Lambda::Function", 7.4),
        ("low", "CVE-2021-3711 OpenSSL SM2 Overflow", ec2_arn(EC2_IDS["prod-app-01"]), "AWS::EC2::Instance", 5.5),
        ("medium", "CVE-2022-1292 OpenSSL c_rehash Command Injection", ec2_arn(EC2_IDS["prod-app-02"]), "AWS::EC2::Instance", 6.8),
        ("high", "CVE-2023-0286 OpenSSL Type Confusion", ec2_arn(EC2_IDS["prod-bastion"]), "AWS::EC2::Instance", 7.4),
        ("medium", "CVE-2022-2068 OpenSSL c_rehash Script Injection", ec2_arn(EC2_IDS["dev-test-01"]), "AWS::EC2::Instance", 6.8),
        ("low", "CVE-2021-45105 Log4j Infinite Recursion", ec2_arn(EC2_IDS["dev-test-02"]), "AWS::EC2::Instance", 5.9),
    ]

    for sev, title, res_arn, res_type, risk in inspector_extra:
        inspector_items.append((
            sev, title,
            f"AWS Inspector finding: {title}. Vulnerability detected on the resource requiring patching.",
            res_arn, res_type, risk, ["NIST SI-2", "PCI DSS 6.3.3"]
        ))

    while len(inspector_items) < 100:
        i = len(inspector_items) % len(inspector_extra)
        sev, title, res_arn, res_type, risk = inspector_extra[i]
        inspector_items.append((
            "low",
            f"Inspector Vulnerability Finding #{len(inspector_items)+1}",
            f"AWS Inspector detected a software vulnerability #{len(inspector_items)+1} on the resource.",
            res_arn, res_type, max(risk * 0.5, 2.0), ["NIST SI-2"]
        ))

    for idx, item in enumerate(inspector_items[:100]):
        sev, title, desc, res_arn, res_type, risk, fw = item
        fid = uid()
        findings.append({
            "id": strip(fid),
            "workspace_id": strip(WORKSPACE_ID),
            "aws_account_id": strip(PROD_ACCOUNT_UUID if "prod" in res_arn else DEV_ACCOUNT_UUID),
            "fingerprint": f"insp-{idx:04d}-" + fid[:8],
            "primary_source": "inspector",
            "severity": sev,
            "status": random.choice(["open", "open", "in_progress"]),
            "risk_score": min(risk, 10.0),
            "title": title,
            "description": desc,
            "remediation": f"Apply vendor patch. Update affected packages. Verify fix with aws inspector2 list-findings.",
            "resource_arn": res_arn,
            "resource_type": res_type,
            "region": "us-east-1",
            "compliance_frameworks": json.dumps(fw),
            "tags": json.dumps({"source": "inspector", "scan_type": "EC2" if "instance" in res_type.lower() else "LAMBDA"}),
            "first_seen_at": days_ago(random.randint(1, 90)),
            "last_seen_at": days_ago(random.randint(0, 14)),
            "resolved_at": None,
            "created_at": days_ago(random.randint(1, 90)),
            "updated_at": days_ago(random.randint(0, 14)),
        })

    # ── D. Config findings (100) ─────────────────────────────────────────────
    config_rules = [
        ("critical", "s3-bucket-public-read-prohibited: FAILED for prod-data-lake",
         "AWS Config rule s3-bucket-public-read-prohibited is non-compliant. prod-data-lake has public read enabled.",
         s3_arn("prod-data-lake"), "AWS::S3::Bucket", 9.0, ["CIS 2.1.5", "PCI DSS 1.3"]),
        ("critical", "rds-instance-public-access-check: FAILED for prod-mysql-01",
         "AWS Config rule rds-instance-public-access-check is non-compliant. prod-mysql-01 is publicly accessible.",
         rds_arn("prod-mysql-01"), "AWS::RDS::DBInstance", 9.5, ["CIS 2.3.1"]),
        ("high", "mfa-enabled-for-iam-console-access: FAILED for admin-user",
         "IAM user admin-user has console password but no MFA device assigned.",
         iam_user_arn("admin-user"), "AWS::IAM::User", 9.0, ["CIS 1.10", "PCI DSS 8.3"]),
        ("high", "iam-root-access-key-check: FAILED",
         "Root account has an active access key. This violates CIS AWS Benchmark control 1.4.",
         f"arn:aws:iam::{PROD_ACCOUNT_ID}:root", "AWS::IAM::User", 9.1, ["CIS 1.4"]),
        ("high", "cloudtrail-enabled: FAILED for dev-trail",
         "AWS Config rule cloudtrail-enabled is non-compliant. dev-trail is not actively logging.",
         trail_arn("dev-trail"), "AWS::CloudTrail::Trail", 8.5, ["CIS 3.1", "PCI DSS 10.1"]),
        ("high", "vpc-flow-logs-enabled: FAILED for prod-vpc",
         "VPC Flow Logs are not enabled for prod-vpc.",
         f"arn:aws:ec2:us-east-1:{PROD_ACCOUNT_ID}:vpc/vpc-prod", "AWS::EC2::VPC", 7.5, ["CIS 3.9"]),
        ("high", "restricted-ssh: FAILED for sg-prod-bastion",
         "Security group sg-prod-bastion allows unrestricted SSH access (0.0.0.0/0:22).",
         sg_arn("sg-prod-bastion"), "AWS::EC2::SecurityGroup", 8.0, ["CIS 5.2"]),
        ("critical", "restricted-common-ports: FAILED for sg-prod-db (3306 open to all)",
         "Security group sg-prod-db allows MySQL (3306) from 0.0.0.0/0.",
         sg_arn("sg-prod-db"), "AWS::EC2::SecurityGroup", 9.8, ["CIS 5.2", "PCI DSS 1.2"]),
        ("high", "encrypted-volumes: FAILED for prod-web-01",
         "EBS volumes attached to prod-web-01 are not encrypted.",
         ec2_arn(EC2_IDS["prod-web-01"]), "AWS::EC2::Instance", 7.5, ["CIS 2.2.1", "HIPAA §164.312(a)(2)(iv)"]),
        ("high", "rds-storage-encrypted: FAILED for prod-mysql-01",
         "prod-mysql-01 RDS storage is not encrypted.",
         rds_arn("prod-mysql-01"), "AWS::RDS::DBInstance", 8.3, ["CIS 2.3.1", "PCI DSS 3.5"]),
        ("medium", "s3-bucket-versioning-enabled: FAILED for prod-financial-reports",
         "S3 versioning is disabled on prod-financial-reports.", s3_arn("prod-financial-reports"), "AWS::S3::Bucket", 6.5, ["CIS 2.1.3"]),
        ("medium", "cloudtrail-s3-dataevents-enabled: FAILED",
         "CloudTrail is not configured to log S3 data events.", trail_arn("prod-trail"), "AWS::CloudTrail::Trail", 6.8, ["CIS 3.7"]),
        ("medium", "iam-password-policy-uppercase-requirement: FAILED",
         "Password policy does not require uppercase characters.", f"arn:aws:iam::{PROD_ACCOUNT_ID}:root", "AWS::IAM::PasswordPolicy", 5.5, ["CIS 1.8"]),
        ("medium", "iam-password-policy-minimum-length: FAILED",
         "Password minimum length is less than 14 characters.", f"arn:aws:iam::{PROD_ACCOUNT_ID}:root", "AWS::IAM::PasswordPolicy", 5.2, ["CIS 1.9"]),
        ("high", "s3-bucket-server-side-encryption-enabled: FAILED for prod-customer-pii",
         "prod-customer-pii does not have server-side encryption enabled.",
         s3_arn("prod-customer-pii"), "AWS::S3::Bucket", 9.3, ["CIS 2.1.1", "HIPAA §164.312(a)(2)(iv)"]),
        ("medium", "lambda-function-settings-check: FAILED (runtime outdated)",
         "Lambda prod-api-handler uses Python 3.8, a deprecated runtime.",
         lambda_arn("prod-api-handler"), "AWS::Lambda::Function", 6.5, ["PCI DSS 6.3.3"]),
        ("medium", "rds-multi-az-support: FAILED for prod-mysql-01",
         "prod-mysql-01 is not configured for Multi-AZ deployment.",
         rds_arn("prod-mysql-01"), "AWS::RDS::DBInstance", 5.5, ["SOC2 A1.1"]),
        ("medium", "ec2-imdsv2-check: FAILED for prod-web-01",
         "IMDSv2 is not required on prod-web-01, leaving it vulnerable to SSRF credential theft.",
         ec2_arn(EC2_IDS["prod-web-01"]), "AWS::EC2::Instance", 6.8, ["CIS 5.7"]),
        ("medium", "access-keys-rotated: FAILED for deploy-user",
         "deploy-user access keys have not been rotated in over 90 days.",
         iam_user_arn("deploy-user"), "AWS::IAM::User", 7.0, ["CIS 1.14"]),
        ("low", "s3-bucket-logging-enabled: FAILED for prod-app-logs",
         "S3 access logging is not enabled on prod-app-logs.",
         s3_arn("prod-app-logs"), "AWS::S3::Bucket", 4.5, ["CIS 2.1.4"]),
    ]

    # Pad Config to 100
    config_extra_arns = [
        (s3_arn("prod-database-backups"), "AWS::S3::Bucket"),
        (ec2_arn(EC2_IDS["prod-app-01"]), "AWS::EC2::Instance"),
        (iam_user_arn("dev-user-1"), "AWS::IAM::User"),
        (rds_arn("dev-mysql-01"), "AWS::RDS::DBInstance"),
        (lambda_arn("dev-test-function"), "AWS::Lambda::Function"),
    ]
    while len(config_rules) < 100:
        i = len(config_rules) % len(config_extra_arns)
        arn, rtype = config_extra_arns[i]
        config_rules.append((
            random.choice(["low", "medium", "low"]),
            f"AWS Config Rule Violation #{len(config_rules)+1}",
            f"AWS Config detected a compliance violation #{len(config_rules)+1} on {arn}.",
            arn, rtype, random.uniform(2.0, 6.0), ["CIS 2.1.1"]
        ))

    for idx, item in enumerate(config_rules[:100]):
        sev, title, desc, res_arn, res_type, risk, fw = item
        fid = uid()
        findings.append({
            "id": strip(fid),
            "workspace_id": strip(WORKSPACE_ID),
            "aws_account_id": strip(PROD_ACCOUNT_UUID if "prod" in res_arn else DEV_ACCOUNT_UUID),
            "fingerprint": f"cfg-{idx:04d}-" + fid[:8],
            "primary_source": "config",
            "severity": sev,
            "status": random.choice(["open", "open", "in_progress", "suppressed"]),
            "risk_score": min(risk, 10.0),
            "title": title,
            "description": desc,
            "remediation": f"Remediate AWS Config rule violation. See AWS Config console for specific remediation steps.",
            "resource_arn": res_arn,
            "resource_type": res_type,
            "region": "us-east-1",
            "compliance_frameworks": json.dumps(fw),
            "tags": json.dumps({"source": "config", "rule_type": "managed"}),
            "first_seen_at": days_ago(random.randint(1, 120)),
            "last_seen_at": days_ago(random.randint(0, 30)),
            "resolved_at": None,
            "created_at": days_ago(random.randint(1, 120)),
            "updated_at": days_ago(random.randint(0, 30)),
        })

    # ── E. IAM Access Analyzer findings (50) ─────────────────────────────────
    aa_items = [
        ("critical", "External Access: prod-data-lake S3 Bucket Allows Public Read",
         "IAM Access Analyzer identified that prod-data-lake allows public read access to external principals.",
         s3_arn("prod-data-lake"), "AWS::S3::Bucket", 9.5, ["CIS 2.1.5", "NIST AC-3"]),
        ("critical", "External Access: github-actions-role Can Be Assumed by Any GitHub Repo",
         "Access Analyzer found github-actions-role can be assumed by any external GitHub Actions principal due to missing OIDC condition.",
         iam_role_arn("github-actions-role"), "AWS::IAM::Role", 10.0, ["CIS 1.16", "NIST AC-6"]),
        ("high", "External Access: prod-customer-pii S3 Bucket Accessible from External Account 234567890123",
         "prod-customer-pii bucket policy grants GetObject to external account 234567890123.",
         s3_arn("prod-customer-pii"), "AWS::S3::Bucket", 8.5, ["HIPAA §164.312(a)", "PCI DSS 3.4"]),
        ("high", "Cross-Account: dev-admin-role Can Be Assumed from Prod Account",
         "dev-admin-role trust policy allows ec2.amazonaws.com from prod account — lateral movement risk.",
         iam_role_arn("dev-admin-role"), "AWS::IAM::Role", 8.0, ["NIST AC-6"]),
        ("high", "Unused Access: admin-user Has 187 Unused Service Permissions",
         "admin-user has not used 187 of their granted permissions in the last 90 days. Violates least privilege principle.",
         iam_user_arn("admin-user"), "AWS::IAM::User", 7.5, ["CIS 1.16", "NIST AC-6"]),
        ("high", "External Access: prod-image-resizer Lambda Has Public Function URL",
         "Lambda prod-image-resizer has a public function URL with no auth restriction.",
         lambda_arn("prod-image-resizer"), "AWS::Lambda::Function", 7.8, ["NIST AC-3"]),
        ("medium", "Unused Access: deploy-user Has 143 Unused Permissions",
         "deploy-user retains permissions for services not used in 90 days.",
         iam_user_arn("deploy-user"), "AWS::IAM::User", 6.5, ["CIS 1.16"]),
        ("medium", "External Access: prod-backups S3 Allows Cross-Account Access",
         "prod-backups has a bucket policy granting access to external AWS account.",
         s3_arn("prod-backups"), "AWS::S3::Bucket", 7.0, ["CIS 2.1.5"]),
        ("high", "Privilege Escalation: sagemaker-execution-role Can Create Roles and Attach Policies",
         "IAM Access Analyzer identified a privilege escalation path via sagemaker-execution-role.",
         iam_role_arn("sagemaker-execution-role"), "AWS::IAM::Role", 8.8, ["NIST AC-6", "CIS 1.16"]),
        ("medium", "Unused Access: ci-cd-user Last Used ec2:* 45 Days Ago",
         "ci-cd-user has ec2:* permissions last used 45 days ago. These should be removed.",
         iam_user_arn("ci-cd-user"), "AWS::IAM::User", 6.0, ["CIS 1.16"]),
        ("medium", "External Access: prod-terraform-state Bucket Policy Too Permissive",
         "Terraform state bucket accessible by all principals in the AWS account without resource constraints.",
         s3_arn("prod-terraform-state"), "AWS::S3::Bucket", 7.0, ["SOC2 CC6.1"]),
        ("high", "Unused Access: ml-engineer-user Has iam:PassRole Never Used",
         "ml-engineer-user has iam:PassRole which has never been used. This is a privilege escalation risk.",
         iam_user_arn("ml-engineer-user"), "AWS::IAM::User", 7.5, ["NIST AC-6"]),
    ]

    # Pad AA to 50
    while len(aa_items) < 50:
        i = len(aa_items) % 5
        aa_items.append((
            "low",
            f"Unused IAM Permission Finding #{len(aa_items)+1}",
            f"IAM Access Analyzer detected unused permissions that violate least privilege principle.",
            iam_user_arn(f"dev-user-{(i%5)+1}"), "AWS::IAM::User",
            random.uniform(3.0, 5.5), ["CIS 1.16", "NIST AC-6"]
        ))

    for idx, item in enumerate(aa_items[:50]):
        sev, title, desc, res_arn, res_type, risk, fw = item
        fid = uid()
        findings.append({
            "id": strip(fid),
            "workspace_id": strip(WORKSPACE_ID),
            "aws_account_id": strip(PROD_ACCOUNT_UUID),
            "fingerprint": f"aa-{idx:04d}-" + fid[:8],
            "primary_source": "iam_access_analyzer",
            "severity": sev,
            "status": random.choice(["open", "open", "in_progress"]),
            "risk_score": min(risk, 10.0),
            "title": title,
            "description": desc,
            "remediation": "Review and remediate IAM Access Analyzer finding. Apply least privilege. Remove external access if unintended.",
            "resource_arn": res_arn,
            "resource_type": res_type,
            "region": "us-east-1",
            "compliance_frameworks": json.dumps(fw),
            "tags": json.dumps({"source": "iam_access_analyzer", "analyzer": "prod-analyzer-01"}),
            "first_seen_at": days_ago(random.randint(1, 90)),
            "last_seen_at": days_ago(random.randint(0, 14)),
            "resolved_at": None,
            "created_at": days_ago(random.randint(1, 90)),
            "updated_at": days_ago(random.randint(0, 14)),
        })

    return findings


def build_graph_nodes(findings):
    """Build 80 security graph nodes linked to relevant findings."""
    ws = strip(WORKSPACE_ID)
    prod_acct = strip(PROD_ACCOUNT_UUID)
    dev_acct = strip(DEV_ACCOUNT_UUID)

    # Index findings by resource_arn for fast lookup
    findings_by_arn = {}
    for f in findings:
        arn = f["resource_arn"]
        if arn not in findings_by_arn:
            findings_by_arn[arn] = []
        findings_by_arn[arn].append(
            str(uuid.UUID(f["id"]))  # restore hyphens for finding_ids
        )

    def node_finding_ids(arn):
        ids = findings_by_arn.get(arn, [])
        return json.dumps(ids[:10])  # cap at 10 per node

    def mk_node(node_type, resource_arn, resource_name, region, aws_acct_id,
                risk_score, is_internet_facing=False, is_sensitive_data=False,
                metadata=None):
        nid = str(uuid.uuid4()).replace("-", "")
        return {
            "id": nid,
            "workspace_id": ws,
            "aws_account_id": aws_acct_id,
            "node_type": node_type,
            "resource_arn": resource_arn,
            "resource_name": resource_name,
            "region": region,
            "risk_score": risk_score,
            "is_internet_facing": 1 if is_internet_facing else 0,
            "is_sensitive_data": 1 if is_sensitive_data else 0,
            "metadata": json.dumps(metadata or {}),
            "finding_ids": node_finding_ids(resource_arn),
            "created_at": days_ago(30),
            "updated_at": days_ago(1),
        }

    nodes = []
    node_map = {}  # name -> node dict

    def add(name, node_type, arn, region, acct, risk, internet=False, sensitive=False, meta=None):
        n = mk_node(node_type, arn, name, region, acct, risk, internet, sensitive, meta)
        nodes.append(n)
        node_map[name] = n
        return n

    # EC2 instances
    for name, iid in EC2_IDS.items():
        arn = ec2_arn(iid)
        internet = name in ("prod-web-01","prod-web-02","prod-web-03","prod-bastion","dev-build-01","dev-test-01","dev-test-02","prod-ml-worker")
        risk = 9.0 if internet else 5.0
        add(name, "ec2_instance", arn, "us-east-1", prod_acct if "prod" in name else dev_acct,
            risk, internet, "db" in name, {"instance_type": "t3.medium", "ami": "ami-0abcdef"})

    # S3 buckets
    s3_sensitivity = {"prod-customer-pii": True, "prod-financial-reports": True, "prod-database-backups": True, "prod-ml-training-data": True, "dev-test-data": True}
    s3_internet = {"prod-data-lake", "prod-app-logs", "dev-build-artifacts", "dev-ml-experiments", "prod-cf-templates"}
    for name, acct, public_read, *_ in [
        ("prod-data-lake","prod",True),("prod-customer-pii","prod",False),
        ("prod-financial-reports","prod",False),("prod-app-logs","prod",True),
        ("prod-backups","prod",False),("dev-test-data","dev",False),
        ("dev-build-artifacts","dev",True),("security-audit-logs","sec",False),
        ("prod-static-assets","prod",False),("prod-ml-training-data","prod",False),
        ("dev-ml-experiments","dev",True),("prod-terraform-state","prod",False),
        ("prod-cf-templates","prod",True),("prod-media-assets","prod",False),
        ("prod-database-backups","prod",False),
    ]:
        a = prod_acct if acct == "prod" else (dev_acct if acct == "dev" else strip(SEC_ACCOUNT_UUID))
        risk = 9.5 if public_read else (7.0 if s3_sensitivity.get(name) else 4.0)
        add(name, "s3_bucket", s3_arn(name), "us-east-1", a, risk,
            name in s3_internet, s3_sensitivity.get(name, False))

    # IAM Roles
    for role in ["prod-ec2-instance-role","prod-lambda-execution-role","dev-admin-role",
                 "prod-ecs-task-role","cross-account-audit-role","github-actions-role",
                 "sagemaker-execution-role","prod-deploy-role"]:
        risk = 9.5 if role in ("github-actions-role","prod-deploy-role","sagemaker-execution-role") else 7.0
        add(role, "iam_role", iam_role_arn(role), "us-east-1", prod_acct, risk,
            role == "github-actions-role", False, {"type": "role"})

    # IAM Users
    for user in ["admin-user","deploy-user","ci-cd-user","data-analyst-user",
                 "ml-engineer-user","dev-user-1","dev-user-2","readonly-user"]:
        risk = 9.0 if user == "admin-user" else (7.0 if user in ("ci-cd-user","deploy-user") else 4.0)
        add(user, "iam_user", iam_user_arn(user), "us-east-1", prod_acct, risk)

    # RDS
    for db, accessible, enc in [
        ("prod-mysql-01", True, False),("prod-postgres-01", False, True),
        ("dev-mysql-01", True, False),("prod-analytics-db", True, False),
        ("prod-aurora-cluster", False, True),
    ]:
        acct = dev_acct if "dev" in db else prod_acct
        risk = 9.5 if accessible and not enc else (6.0 if accessible else 3.5)
        add(db, "rds_instance", rds_arn(db), "us-east-1", acct, risk, accessible, True)

    # Lambda
    for fn in ["prod-api-handler","prod-data-processor","prod-auth-service",
               "prod-payment-processor","dev-test-function","prod-image-resizer",
               "prod-etl-job","prod-ml-inference"]:
        risk = 9.5 if fn in ("prod-payment-processor","prod-api-handler") else 6.0
        internet = fn in ("prod-image-resizer","prod-ml-inference")
        add(fn, "lambda_function", lambda_arn(fn), "us-east-1", prod_acct, risk, internet)

    # Security Groups
    for sg in ["sg-prod-web","sg-prod-app","sg-prod-db","sg-prod-bastion",
               "sg-dev-open","sg-prod-internal","sg-prod-ecs","sg-prod-redis",
               "sg-prod-elasticsearch","sg-prod-ml"]:
        risk = 9.8 if sg in ("sg-prod-db","sg-dev-open","sg-prod-redis","sg-prod-elasticsearch","sg-prod-ml") else 6.0
        add(sg, "security_group", sg_arn(sg), "us-east-1", prod_acct, risk)

    # VPCs
    add("prod-vpc", "vpc", f"arn:aws:ec2:us-east-1:{PROD_ACCOUNT_ID}:vpc/vpc-prod",
        "us-east-1", prod_acct, 6.5, False, False, {"cidr": "10.0.0.0/16", "flow_logs": False})
    add("dev-vpc", "vpc", f"arn:aws:ec2:us-east-1:{DEV_ACCOUNT_ID}:vpc/vpc-dev",
        "us-east-1", dev_acct, 7.0, False, False, {"cidr": "172.16.0.0/16", "flow_logs": False})

    # Subnets
    for i in range(1, 4):
        add(f"prod-public-subnet-{i}", "subnet",
            f"arn:aws:ec2:us-east-1:{PROD_ACCOUNT_ID}:subnet/subnet-pub-{i:02d}",
            "us-east-1", prod_acct, 5.0, True)
        add(f"prod-private-subnet-{i}", "subnet",
            f"arn:aws:ec2:us-east-1:{PROD_ACCOUNT_ID}:subnet/subnet-priv-{i:02d}",
            "us-east-1", prod_acct, 3.0)

    # Internet Gateways
    add("prod-igw", "internet_gateway",
        f"arn:aws:ec2:us-east-1:{PROD_ACCOUNT_ID}:internet-gateway/igw-prod",
        "us-east-1", prod_acct, 5.0, True)
    add("dev-igw", "internet_gateway",
        f"arn:aws:ec2:us-east-1:{DEV_ACCOUNT_ID}:internet-gateway/igw-dev",
        "us-east-1", dev_acct, 6.0, True)

    # ECS/EKS
    add("prod-ecs-cluster", "ecs_cluster",
        f"arn:aws:ecs:us-east-1:{PROD_ACCOUNT_ID}:cluster/prod-ecs-cluster",
        "us-east-1", prod_acct, 8.5, False, False, {"privileged_tasks": True})
    add("prod-eks-cluster", "eks_cluster",
        f"arn:aws:eks:us-east-1:{PROD_ACCOUNT_ID}:cluster/prod-eks-cluster",
        "us-east-1", prod_acct, 8.0, True, False, {"version": "1.25", "public_endpoint": True})

    # KMS
    for kname in ["prod-cmk-s3","prod-cmk-rds","prod-cmk-overpermissive"]:
        risk = 8.0 if "overpermissive" in kname else 4.0
        add(kname, "kms_key",
            f"arn:aws:kms:us-east-1:{PROD_ACCOUNT_ID}:key/{kname}",
            "us-east-1", prod_acct, risk)

    # Secrets
    for sname in ["prod-db-password","prod-stripe-key","prod-oauth-secret",
                  "prod-jwt-secret","prod-github-token"]:
        add(sname, "secret", secret_arn(sname), "us-east-1", prod_acct, 7.5, False, True)

    # CloudTrails
    add("prod-trail", "cloudtrail", trail_arn("prod-trail"), "us-east-1", prod_acct, 7.0)
    add("dev-trail", "cloudtrail", trail_arn("dev-trail"), "us-east-1", dev_acct, 9.0)

    # Load Balancers
    for lb in ["prod-web-alb","prod-api-alb","prod-internal-nlb"]:
        internet = "internal" not in lb
        add(lb, "load_balancer",
            f"arn:aws:elasticloadbalancing:us-east-1:{PROD_ACCOUNT_ID}:loadbalancer/app/{lb}/abcdef",
            "us-east-1", prod_acct, 6.0 if internet else 3.5, internet)

    # API Gateways
    for apigw in ["prod-api-gateway","prod-internal-api"]:
        add(apigw, "api_gateway",
            f"arn:aws:apigateway:us-east-1::{apigw}",
            "us-east-1", prod_acct, 7.0, True)

    # SageMaker
    add("prod-ml-endpoint", "sagemaker_endpoint",
        f"arn:aws:sagemaker:us-east-1:{PROD_ACCOUNT_ID}:endpoint/prod-ml-endpoint",
        "us-east-1", prod_acct, 8.0, True)

    return nodes, node_map


def build_edges(node_map):
    """Build 120 security graph edges."""
    ws = strip(WORKSPACE_ID)
    edges = []

    def mk_edge(source_name, target_name, edge_type, is_attack_path=False, risk=0.5, meta=None):
        src = node_map.get(source_name)
        tgt = node_map.get(target_name)
        if not src or not tgt:
            return None
        eid = str(uuid.uuid4()).replace("-", "")
        return {
            "id": eid,
            "workspace_id": ws,
            "source_node_id": src["id"],
            "target_node_id": tgt["id"],
            "edge_type": edge_type,
            "is_attack_path": 1 if is_attack_path else 0,
            "risk_contribution": risk,
            "metadata": json.dumps(meta or {}),
            "created_at": days_ago(30),
            "updated_at": days_ago(1),
        }

    def add(src, tgt, etype, attack=False, risk=0.5, meta=None):
        e = mk_edge(src, tgt, etype, attack, risk, meta)
        if e:
            edges.append(e)

    # Internet-facing connections
    add("prod-igw", "prod-web-01", "ROUTES_TO", True, 0.9)
    add("prod-igw", "prod-web-02", "ROUTES_TO", True, 0.9)
    add("prod-igw", "prod-web-03", "ROUTES_TO", True, 0.9)
    add("prod-igw", "prod-bastion", "ROUTES_TO", True, 0.95)
    add("prod-igw", "dev-igw", "PEERED_WITH", False, 0.7)

    # SG associations
    add("sg-prod-web", "prod-web-01", "PROTECTS", True, 0.85)
    add("sg-prod-web", "prod-web-02", "PROTECTS", True, 0.85)
    add("sg-prod-web", "prod-web-03", "PROTECTS", True, 0.85)
    add("sg-prod-app", "prod-app-01", "PROTECTS", False, 0.6)
    add("sg-prod-app", "prod-app-02", "PROTECTS", False, 0.6)
    add("sg-prod-db", "prod-mysql-01", "PROTECTS", True, 0.99)
    add("sg-prod-bastion", "prod-bastion", "PROTECTS", True, 0.9)
    add("sg-dev-open", "dev-test-01", "PROTECTS", True, 0.95)
    add("sg-dev-open", "dev-test-02", "PROTECTS", True, 0.95)
    add("sg-dev-open", "dev-build-01", "PROTECTS", True, 0.95)
    add("sg-prod-redis", "prod-app-01", "PROTECTS", True, 0.85)
    add("sg-prod-elasticsearch", "prod-app-02", "PROTECTS", True, 0.9)
    add("sg-prod-ml", "prod-ml-worker", "PROTECTS", True, 0.9)
    add("sg-prod-ecs", "prod-ecs-host", "PROTECTS", False, 0.5)

    # IAM role assignments
    add("prod-ec2-instance-role", "prod-web-01", "ASSIGNED_TO", True, 0.9)
    add("prod-ec2-instance-role", "prod-app-01", "ASSIGNED_TO", True, 0.9)
    add("prod-lambda-execution-role", "prod-api-handler", "ASSIGNED_TO", True, 0.8)
    add("prod-lambda-execution-role", "prod-data-processor", "ASSIGNED_TO", True, 0.8)
    add("sagemaker-execution-role", "prod-ml-worker", "ASSIGNED_TO", True, 0.9)
    add("prod-ecs-task-role", "prod-ecs-host", "ASSIGNED_TO", True, 0.7)
    add("prod-deploy-role", "ci-cd-user", "CAN_BE_ASSUMED_BY", True, 0.95)
    add("github-actions-role", "prod-deploy-role", "CAN_ASSUME", True, 0.99)
    add("dev-admin-role", "dev-test-01", "ASSIGNED_TO", True, 0.8)

    # Data access
    add("prod-ec2-instance-role", "prod-customer-pii", "HAS_ACCESS_TO", True, 0.95)
    add("prod-ec2-instance-role", "prod-financial-reports", "HAS_ACCESS_TO", True, 0.85)
    add("prod-ec2-instance-role", "prod-data-lake", "HAS_ACCESS_TO", True, 0.9)
    add("prod-lambda-execution-role", "prod-customer-pii", "HAS_ACCESS_TO", True, 0.8)
    add("prod-ecs-task-role", "prod-db-password", "HAS_ACCESS_TO", True, 0.75)
    add("prod-ecs-task-role", "prod-stripe-key", "HAS_ACCESS_TO", True, 0.9)
    add("prod-api-handler", "prod-mysql-01", "CONNECTS_TO", True, 0.9)
    add("prod-api-handler", "prod-db-password", "READS_SECRET", True, 0.85)
    add("prod-etl-job", "prod-customer-pii", "READS_FROM", False, 0.5)
    add("prod-etl-job", "prod-analytics-db", "WRITES_TO", False, 0.4)

    # Network flows
    add("prod-web-01", "prod-app-01", "CONNECTS_TO", False, 0.5)
    add("prod-web-02", "prod-app-01", "CONNECTS_TO", False, 0.5)
    add("prod-web-03", "prod-app-02", "CONNECTS_TO", False, 0.5)
    add("prod-app-01", "prod-mysql-01", "CONNECTS_TO", False, 0.4)
    add("prod-app-02", "prod-postgres-01", "CONNECTS_TO", False, 0.3)
    add("prod-app-01", "prod-app-02", "CONNECTS_TO", False, 0.3)
    add("prod-bastion", "prod-app-01", "SSH_ACCESS_TO", True, 0.8)
    add("prod-bastion", "prod-db-01", "SSH_ACCESS_TO", True, 0.85)
    add("prod-web-alb", "prod-web-01", "ROUTES_TO", False, 0.5)
    add("prod-web-alb", "prod-web-02", "ROUTES_TO", False, 0.5)
    add("prod-api-alb", "prod-app-01", "ROUTES_TO", False, 0.4)
    add("prod-api-gateway", "prod-api-handler", "TRIGGERS", False, 0.5)
    add("prod-api-gateway", "prod-auth-service", "TRIGGERS", False, 0.3)

    # VPC topology
    add("prod-vpc", "prod-public-subnet-1", "CONTAINS", False, 0.3)
    add("prod-vpc", "prod-public-subnet-2", "CONTAINS", False, 0.3)
    add("prod-vpc", "prod-public-subnet-3", "CONTAINS", False, 0.3)
    add("prod-vpc", "prod-private-subnet-1", "CONTAINS", False, 0.2)
    add("prod-vpc", "prod-private-subnet-2", "CONTAINS", False, 0.2)
    add("prod-vpc", "prod-private-subnet-3", "CONTAINS", False, 0.2)
    add("prod-public-subnet-1", "prod-web-01", "HOSTS", False, 0.4)
    add("prod-public-subnet-2", "prod-web-02", "HOSTS", False, 0.4)
    add("prod-private-subnet-1", "prod-app-01", "HOSTS", False, 0.3)
    add("prod-private-subnet-2", "prod-mysql-01", "HOSTS", False, 0.3)

    # ECS/EKS
    add("prod-ecs-cluster", "prod-ecs-host", "RUNS_ON", True, 0.8)
    add("prod-eks-cluster", "prod-ecs-host", "MANAGES", False, 0.5)

    # KMS
    add("prod-cmk-rds", "prod-postgres-01", "ENCRYPTS", False, 0.2)
    add("prod-cmk-s3", "security-audit-logs", "ENCRYPTS", False, 0.2)
    add("prod-cmk-overpermissive", "prod-data-lake", "ENCRYPTS", False, 0.5)

    # CloudTrail
    add("prod-trail", "security-audit-logs", "LOGS_TO", False, 0.2)
    add("dev-trail", "security-audit-logs", "LOGS_TO", False, 0.2)

    # ML
    add("prod-ml-worker", "prod-ml-training-data", "READS_FROM", False, 0.5)
    add("prod-ml-worker", "prod-ml-endpoint", "DEPLOYS_TO", False, 0.4)
    add("sagemaker-execution-role", "prod-ml-training-data", "HAS_ACCESS_TO", False, 0.5)

    # Attack-path specific edges
    add("sg-prod-db", "prod-mysql-01", "EXPOSES", True, 0.99, {"port": 3306, "cidr": "0.0.0.0/0"})
    add("prod-data-lake", "prod-app-01", "DATA_ACCESS_ENABLES", True, 0.85)
    add("github-actions-role", "prod-deploy-role", "PRIVILEGE_ESCALATION_TO", True, 0.99)
    add("sagemaker-execution-role", "admin-user", "PRIVILEGE_ESCALATION_PATH", True, 0.9)
    add("prod-ecs-cluster", "prod-ec2-instance-role", "CONTAINER_ESCAPE_TO", True, 0.85)
    add("dev-admin-role", "prod-deploy-role", "LATERAL_MOVEMENT_TO", True, 0.8)
    add("dev-trail", "prod-deploy-role", "ENABLES_UNDETECTED_ACCESS", True, 0.7)
    add("prod-api-handler", "prod-db-password", "SECRET_EXPOSURE", True, 0.95)

    # Additional edges to reach 120
    extra_pairs = [
        ("prod-web-01", "prod-mysql-01", "CONNECTS_TO", False, 0.3),
        ("prod-web-02", "prod-postgres-01", "CONNECTS_TO", False, 0.3),
        ("prod-web-03", "prod-analytics-db", "CONNECTS_TO", False, 0.4),
        ("ci-cd-user", "prod-deploy-role", "CAN_ASSUME", True, 0.9),
        ("admin-user", "prod-data-lake", "HAS_ACCESS_TO", False, 0.6),
        ("data-analyst-user", "prod-analytics-db", "CONNECTS_TO", False, 0.4),
        ("ml-engineer-user", "prod-ml-training-data", "HAS_ACCESS_TO", False, 0.4),
        ("prod-internal-api", "prod-auth-service", "TRIGGERS", False, 0.3),
        ("prod-internal-nlb", "prod-app-01", "ROUTES_TO", False, 0.4),
        ("prod-internal-nlb", "prod-app-02", "ROUTES_TO", False, 0.4),
        ("prod-payment-processor", "prod-stripe-key", "HARDCODED_SECRET", True, 0.99),
        ("dev-test-function", "dev-admin-role", "USES_ADMIN_ROLE", True, 0.9),
        ("dev-build-01", "dev-test-01", "SAME_NETWORK_AS", False, 0.5),
        ("dev-test-01", "prod-aurora-cluster", "CONNECTS_TO", False, 0.6),
        ("prod-ml-inference", "prod-ml-training-data", "READS_FROM", False, 0.4),
    ]
    for src, tgt, etype, attack, risk, *_ in extra_pairs:
        add(src, tgt, etype, attack, risk)

    return edges


def build_attack_paths(node_map, findings):
    """Build 8 attack paths."""
    ws = strip(WORKSPACE_ID)

    def node_id(name):
        n = node_map.get(name)
        return n["id"] if n else None

    def path_finding_ids(names):
        ids = []
        for f in findings:
            for name in names:
                n = node_map.get(name)
                if n and f["resource_arn"] == n.get("resource_arn"):
                    ids.append(str(uuid.UUID(f["id"])))
        return json.dumps(list(set(ids))[:8])

    def mk_path(name, severity, description, node_names, edge_types, blast_radius, tags, entry_name, target_name):
        pid = str(uuid.uuid4()).replace("-", "")
        node_ids = [nid for nid in [node_id(n) for n in node_names] if nid]
        edge_ids = [str(uuid.uuid4()) for _ in edge_types]
        return {
            "id": pid,
            "workspace_id": ws,
            "name": name,
            "description": description,
            "severity": severity,
            "node_path": json.dumps(node_ids),
            "edge_path": json.dumps(edge_ids),
            "toxic_combo_tags": json.dumps(tags),
            "blast_radius": blast_radius,
            "entry_node_id": node_id(entry_name),
            "target_node_id": node_id(target_name),
            "entry_description": f"Entry: {entry_name}",
            "target_description": f"Target: {target_name}",
            "is_active": 1,
            "related_finding_ids": path_finding_ids(node_names),
            "created_at": days_ago(14),
            "updated_at": days_ago(1),
        }

    paths = [
        mk_path(
            "Internet to Production Database via Misconfigured Security Group",
            "critical",
            "An attacker can reach the production MySQL database directly from the internet via sg-prod-db which allows 0.0.0.0/0 on port 3306. The database is also publicly accessible and unencrypted.",
            ["prod-igw", "sg-prod-db", "prod-mysql-01", "prod-customer-pii"],
            ["ROUTES_TO", "EXPOSES", "CONNECTED_TO", "DATA_STORED_IN"],
            1200, ["PUBLIC_DB", "NO_ENCRYPTION", "PII_EXPOSURE", "CRIT_SG"], "prod-igw", "prod-customer-pii"
        ),
        mk_path(
            "Public S3 to IAM Privilege Escalation",
            "critical",
            "An attacker exploiting the public prod-data-lake S3 bucket can obtain AWS credentials via SSRF on prod-app-01, then use the prod-ec2-instance-role (which has s3:* + iam:PassRole) to escalate to prod-deploy-role (AdministratorAccess).",
            ["prod-data-lake", "prod-app-01", "prod-ec2-instance-role", "prod-deploy-role"],
            ["DATA_ACCESS_ENABLES", "USES_ROLE", "PASS_ROLE_TO", "ASSUMES"],
            3500, ["PUBLIC_S3", "IAM_PASSROLE", "ADMIN_ESCALATION", "SSRF_RISK"], "prod-data-lake", "prod-deploy-role"
        ),
        mk_path(
            "GitHub Actions Any-Repo Assume Role to Admin",
            "critical",
            "The github-actions-role is missing an OIDC sub condition, allowing any GitHub Actions workflow from any repository to assume it and then pivot to prod-deploy-role (AdministratorAccess) — full production account takeover.",
            ["github-actions-role", "prod-deploy-role", "prod-customer-pii", "prod-mysql-01"],
            ["PRIVILEGE_ESCALATION_TO", "ASSUMES", "HAS_ACCESS_TO", "HAS_ACCESS_TO"],
            5000, ["OIDC_MISCONFIGURATION", "ANY_REPO", "ADMIN_ESCALATION", "SUPPLY_CHAIN"], "github-actions-role", "prod-deploy-role"
        ),
        mk_path(
            "Lambda Secret Exposure to RDS Data Breach",
            "high",
            "prod-api-handler Lambda contains the database password in plaintext environment variables. An attacker who reads Lambda configuration (e.g. via IAM enumeration) gets direct RDS access to prod-mysql-01.",
            ["prod-api-handler", "prod-db-password", "prod-mysql-01"],
            ["SECRET_EXPOSURE", "AUTHENTICATES_TO", "DATA_ACCESS"],
            800, ["SECRET_IN_ENV_VAR", "PLAINTEXT_CREDENTIAL", "RDS_ACCESS"], "prod-api-handler", "prod-mysql-01"
        ),
        mk_path(
            "ECS Privileged Container Escape to Host and Role Escalation",
            "high",
            "The ECS task prod-privileged-task runs with privileged=true. A container compromise leads to host EC2 escape (prod-ecs-host), then to the prod-ec2-instance-role with s3:* + iam:PassRole, enabling full S3 and role escalation.",
            ["prod-ecs-cluster", "prod-ecs-host", "prod-ec2-instance-role", "prod-customer-pii"],
            ["CONTAINER_ESCAPE_TO", "INSTANCE_ROLE", "HAS_ACCESS_TO", "DATA_EXPOSURE"],
            2000, ["PRIVILEGED_CONTAINER", "CONTAINER_ESCAPE", "IAM_PASSROLE", "PII_EXPOSURE"], "prod-ecs-cluster", "prod-customer-pii"
        ),
        mk_path(
            "SageMaker Privilege Escalation to Administrator",
            "high",
            "prod-ml-worker has Jupyter (port 8888) exposed to the internet. An attacker compromising Jupyter gains code execution, then uses sagemaker-execution-role (which has iam:CreateRole + iam:AttachRolePolicy) to create an admin role.",
            ["prod-ml-worker", "sagemaker-execution-role", "prod-deploy-role"],
            ["JUPYTER_RCE", "USES_ROLE", "PRIVILEGE_ESCALATION_TO"],
            4000, ["JUPYTER_EXPOSED", "IAM_CREATE_ROLE", "PRIV_ESC", "ADMIN_TAKEOVER"], "prod-ml-worker", "prod-deploy-role"
        ),
        mk_path(
            "Dev Account Lateral Movement to Production",
            "high",
            "dev-admin-role in the dev account (with AdministratorAccess) can assume roles in the prod account. An attacker compromising dev-test-01 can pivot to prod resources via cross-account AssumeRole.",
            ["dev-test-01", "dev-admin-role", "prod-deploy-role", "prod-customer-pii"],
            ["USES_ROLE", "CROSS_ACCOUNT_ASSUME", "PIVOTS_TO", "DATA_ACCESS"],
            3000, ["CROSS_ACCOUNT_ACCESS", "LATERAL_MOVEMENT", "DEV_TO_PROD"], "dev-test-01", "prod-customer-pii"
        ),
        mk_path(
            "CloudTrail Disabled — Attacker Operates Undetected in Dev",
            "medium",
            "dev-trail is not logging. Any API action in the dev account is undetected. An attacker can perform reconnaissance, escalate privileges, and pivot to prod without generating audit records.",
            ["dev-trail", "dev-test-01", "dev-admin-role", "prod-deploy-role"],
            ["ENABLES_UNDETECTED_ACCESS", "USES_ROLE", "LATERAL_MOVEMENT_TO", "ASSUMES"],
            1500, ["CLOUDTRAIL_DISABLED", "NO_AUDIT_LOG", "DEV_TO_PROD"], "dev-trail", "prod-deploy-role"
        ),
    ]

    return paths


def build_intelligence_records(findings):
    """Build finding intelligence records covering RED / AMBER / GREEN tiers."""
    ws = strip(WORKSPACE_ID)
    records = []

    # ── Select findings to analyse (realistic enterprise profile) ──────────
    # RED  → risk_score >= 7.5  OR  severity=critical               (~60)
    # AMBER→ risk_score 4.0-7.4 OR  severity=high/medium+public     (~180)
    # GREEN→ risk_score < 4.0   OR  severity=low/informational      (sample 80)
    red_pool   = [f for f in findings if f["risk_score"] >= 7.5 or f["severity"] == "critical"]
    amber_pool = [f for f in findings if 4.0 <= f["risk_score"] < 7.5 and f["severity"] in ("high","medium")]
    green_pool = [f for f in findings if f["risk_score"] < 4.0 or f["severity"] in ("low","informational")]

    selected = (
        red_pool[:60] +
        amber_pool[:150] +
        green_pool[:80]
    )

    # Deduplicate by id
    seen = set()
    unique = []
    for f in selected:
        if f["id"] not in seen:
            seen.add(f["id"])
            unique.append(f)
    selected = unique

    def _rag_for(f):
        score = f["risk_score"]
        sev   = f["severity"]
        if score >= 7.5 or sev == "critical":
            return "RED", 1 if score >= 9.5 else 3
        if score >= 4.0 or sev in ("high", "medium"):
            return "AMBER", 7 if score >= 6.0 else 14
        return "GREEN", 30 if sev == "low" else 60

    rag_map = {}  # unused — kept for compat
    for f in selected:
        sev = f["severity"]
        rag, sla = _rag_for(f)

        iid = str(uuid.uuid4()).replace("-", "")
        fid_with_hyphens = str(uuid.UUID(f["id"]))

        records.append({
            "id": iid,
            "workspace_id": ws,
            "finding_id": f["id"],
            "what_is_it": f"Security finding: {f['title'][:200]}",
            "current_state": f"Resource {f['resource_arn']} is misconfigured or vulnerable.",
            "expected_state": "Resource should comply with security best practices and organisational policy.",
            "business_impact": f"This {sev}-severity finding poses a {rag} risk to the organisation. Exploitation could result in data breach, compliance violation, or service disruption.",
            "attack_scenario": f"An attacker could exploit this finding to gain unauthorized access, escalate privileges, or exfiltrate sensitive data. MITRE ATT&CK mapping: T1190 (Exploit Public-Facing Application) or T1078 (Valid Accounts).",
            "composite_score": f["risk_score"],
            "primary_root_cause": "misconfiguration" if f["primary_source"] in ("security_hub","config") else "vulnerability",
            "causal_factors": json.dumps(["configuration_drift", "missing_controls", "inadequate_monitoring"]),
            "causal_chain": json.dumps([
                {"step": 1, "description": "Resource deployed without security review"},
                {"step": 2, "description": "Default/permissive configuration retained"},
                {"step": 3, "description": "No automated detection in place"},
            ]),
            "toxic_combinations": json.dumps([]),
            "blast_radius_count": random.randint(5, 50),
            "confidence": 0.92,
            "rag_level": rag,
            "rag_composite_score": f["risk_score"],
            "rag_primary_reason": f"Risk score {f['risk_score']:.1f} with {sev} severity and active status.",
            "sla_days": sla,
            "escalation_required": 1 if rag == "RED" else 0,
            "stakeholders": json.dumps(["security-team@company.com", "platform-team@company.com"]),
            "immediate_actions": json.dumps([
                f"1. Assess impact of {f['title'][:80]}",
                "2. Notify security team and resource owner",
                "3. Apply immediate mitigation if possible",
            ]),
            "sprint_actions": json.dumps([
                "Schedule remediation sprint",
                "Update runbooks",
                "Add to security backlog",
            ]),
            "quarterly_actions": json.dumps([
                "Review security posture",
                "Update compliance documentation",
                "Conduct security training",
            ]),
            "ollama_model": "llama3",
            "fallback_used": 1,
            "generation_status": "completed",
            "error_message": None,
            "created_at": days_ago(7),
            "updated_at": days_ago(1),
        })

    return records


def get_all_data():
    findings = build_findings()
    nodes, node_map = build_graph_nodes(findings)
    edges = build_edges(node_map)
    attack_paths = build_attack_paths(node_map, findings)
    intelligence = build_intelligence_records(findings)
    return findings, nodes, edges, attack_paths, intelligence


EC2_IDS = {
    "prod-web-01":   "i-0a1b2c3d4e5f00001",
    "prod-web-02":   "i-0a1b2c3d4e5f00002",
    "prod-web-03":   "i-0a1b2c3d4e5f00003",
    "prod-app-01":   "i-0a1b2c3d4e5f00004",
    "prod-app-02":   "i-0a1b2c3d4e5f00005",
    "prod-db-01":    "i-0a1b2c3d4e5f00006",
    "prod-bastion":  "i-0a1b2c3d4e5f00007",
    "dev-build-01":  "i-0a1b2c3d4e5f00008",
    "dev-test-01":   "i-0a1b2c3d4e5f00009",
    "dev-test-02":   "i-0a1b2c3d4e5f00010",
    "prod-ml-worker":"i-0a1b2c3d4e5f00011",
    "prod-ecs-host": "i-0a1b2c3d4e5f00012",
}

if __name__ == "__main__":
    findings, nodes, edges, attack_paths, intelligence = get_all_data()
    print(f"Findings: {len(findings)}")
    print(f"Nodes: {len(nodes)}")
    print(f"Edges: {len(edges)}")
    print(f"Attack Paths: {len(attack_paths)}")
    print(f"Intelligence Records: {len(intelligence)}")
    rag = {"RED": 0, "AMBER": 0, "GREEN": 0}
    for i in intelligence:
        rag[i["rag_level"]] = rag.get(i["rag_level"], 0) + 1
    print(f"RAG: RED={rag['RED']}, AMBER={rag['AMBER']}, GREEN={rag['GREEN']}")
