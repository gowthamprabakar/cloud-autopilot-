#!/usr/bin/env python3
"""
Cloud Posture — LocalStack Ingestion Script
Connects to LocalStack at http://localhost:4566, calls real AWS APIs,
normalises findings to the canonical_findings schema, and upserts into demo.db.

Prerequisites: LocalStack running + bootstrap_localstack.py already executed.
"""
import sys
import os
import sqlite3
import json
import uuid
import hashlib
from datetime import datetime

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError
except ImportError:
    print("ERROR: boto3 not installed. Run: pip install boto3")
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(os.path.dirname(SCRIPT_DIR), "demo.db")
WORKSPACE_ID = "7ed72074-8a71-4062-9a3c-55fc195dd878"
PROD_ACCOUNT_UUID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

ENDPOINT = "http://localhost:4566"
BOTO_CFG = Config(retries={"max_attempts": 2, "mode": "standard"})

COMMON = dict(
    endpoint_url=ENDPOINT,
    aws_access_key_id="test",
    aws_secret_access_key="test",
    region_name="us-east-1",
    config=BOTO_CFG,
)


def strip(u): return u.replace("-", "")
def uid(): return str(uuid.uuid4()).replace("-", "")
def now(): return datetime.utcnow().isoformat()


def client(service):
    return boto3.client(service, **COMMON)


def fingerprint(source, resource_id, check_id):
    raw = f"{source}:{resource_id}:{check_id}"
    return hashlib.sha256(raw.encode()).hexdigest()[:64]


def connect_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode=WAL")
    return con


def upsert_finding(con, f):
    """Insert-or-update a canonical finding."""
    existing = con.execute(
        "SELECT id FROM canonical_findings WHERE fingerprint=? AND workspace_id=?",
        (f["fingerprint"], f["workspace_id"])
    ).fetchone()

    if existing:
        con.execute(
            "UPDATE canonical_findings SET last_seen_at=?, updated_at=?, status=? WHERE fingerprint=? AND workspace_id=?",
            (f["last_seen_at"], f["updated_at"], f["status"], f["fingerprint"], f["workspace_id"])
        )
        return "updated"
    else:
        con.execute(
            """INSERT INTO canonical_findings
               (id,workspace_id,aws_account_id,fingerprint,primary_source,severity,
                status,risk_score,title,description,remediation,resource_arn,
                resource_type,region,compliance_frameworks,tags,
                first_seen_at,last_seen_at,resolved_at,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                f["id"], f["workspace_id"], f["aws_account_id"], f["fingerprint"],
                f["primary_source"], f["severity"], f["status"], f["risk_score"],
                f["title"], f["description"], f["remediation"], f["resource_arn"],
                f["resource_type"], f["region"], f["compliance_frameworks"], f["tags"],
                f["first_seen_at"], f["last_seen_at"], f.get("resolved_at"),
                f["created_at"], f["updated_at"],
            )
        )
        return "inserted"


# ── Security Hub ─────────────────────────────────────────────────────────────

def severity_label_to_str(label):
    mapping = {"CRITICAL": "critical", "HIGH": "high", "MEDIUM": "medium",
               "LOW": "low", "INFORMATIONAL": "informational"}
    return mapping.get(str(label).upper(), "medium")


def ingest_security_hub(con):
    print("  Ingesting Security Hub findings...")
    try:
        sh = client("securityhub")
        paginator = sh.get_paginator("get_findings")
        inserted = updated = skipped = 0
        ws_id = strip(WORKSPACE_ID)
        acct_id = strip(PROD_ACCOUNT_UUID)

        for page in paginator.paginate(Filters={"RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}]}):
            for f in page.get("Findings", []):
                sev_label = f.get("Severity", {}).get("Label", "MEDIUM")
                sev = severity_label_to_str(sev_label)
                score = f.get("Severity", {}).get("Normalized", 50) / 10.0
                res = f.get("Resources", [{}])[0]
                res_arn = res.get("Id", "")
                res_type = res.get("Type", "Other")
                fp = fingerprint("security_hub", res_arn, f.get("GeneratorId", ""))

                finding = {
                    "id": uid(),
                    "workspace_id": ws_id,
                    "aws_account_id": acct_id,
                    "fingerprint": fp,
                    "primary_source": "security_hub",
                    "severity": sev,
                    "status": "open",
                    "risk_score": round(score, 1),
                    "title": f.get("Title", "Security Hub Finding")[:500],
                    "description": f.get("Description", "")[:2000],
                    "remediation": (f.get("Remediation", {}).get("Recommendation", {}).get("Text", ""))[:2000],
                    "resource_arn": res_arn,
                    "resource_type": res_type,
                    "region": f.get("Region", "us-east-1"),
                    "compliance_frameworks": json.dumps([
                        c.get("StandardsControlArn", "") for c in f.get("Compliance", {}).get("RelatedRequirements", [])
                    ][:5]),
                    "tags": json.dumps({"source": "security_hub", "product": f.get("ProductName", "")}),
                    "first_seen_at": f.get("FirstObservedAt", now()),
                    "last_seen_at": f.get("LastObservedAt", now()),
                    "resolved_at": None,
                    "created_at": now(),
                    "updated_at": now(),
                }
                result = upsert_finding(con, finding)
                if result == "inserted":
                    inserted += 1
                else:
                    updated += 1

        con.commit()
        print(f"    Security Hub: inserted={inserted}, updated={updated}, skipped={skipped}")
    except ClientError as e:
        print(f"    Security Hub not available: {e.response['Error']['Code']}")


# ── GuardDuty ────────────────────────────────────────────────────────────────

def ingest_guardduty(con):
    print("  Ingesting GuardDuty findings...")
    try:
        gd = client("guardduty")
        detectors = gd.list_detectors().get("DetectorIds", [])
        if not detectors:
            print("    No GuardDuty detectors found in LocalStack")
            return

        detector_id = detectors[0]
        finding_ids_resp = gd.list_findings(DetectorId=detector_id,
                                             FindingCriteria={"Criterion": {"service.archived": {"Eq": ["false"]}}})
        finding_ids = finding_ids_resp.get("FindingIds", [])
        if not finding_ids:
            print("    No GuardDuty findings in LocalStack")
            return

        ws_id = strip(WORKSPACE_ID)
        acct_id = strip(PROD_ACCOUNT_UUID)
        inserted = updated = 0

        for batch_start in range(0, len(finding_ids), 50):
            batch = finding_ids[batch_start:batch_start+50]
            findings = gd.get_findings(DetectorId=detector_id, FindingIds=batch).get("Findings", [])

            for f in findings:
                sev_num = f.get("Severity", 5.0)
                if sev_num >= 9: sev = "critical"
                elif sev_num >= 7: sev = "high"
                elif sev_num >= 4: sev = "medium"
                else: sev = "low"

                res = f.get("Resource", {})
                res_arn = (res.get("InstanceDetails", {}).get("InstanceArn") or
                           res.get("S3BucketDetails", [{}])[0].get("Arn") if res.get("S3BucketDetails") else
                           res.get("AccessKeyDetails", {}).get("UserName") or f["Id"])
                res_type = res.get("ResourceType", "Other")

                fp = fingerprint("guard_duty", str(res_arn), f.get("Type", ""))
                finding = {
                    "id": uid(),
                    "workspace_id": ws_id,
                    "aws_account_id": acct_id,
                    "fingerprint": fp,
                    "primary_source": "guard_duty",
                    "severity": sev,
                    "status": "open",
                    "risk_score": min(sev_num, 10.0),
                    "title": f.get("Title", "GuardDuty Finding")[:500],
                    "description": f.get("Description", "")[:2000],
                    "remediation": "Investigate the GuardDuty finding and take appropriate incident response actions.",
                    "resource_arn": str(res_arn),
                    "resource_type": res_type,
                    "region": f.get("Region", "us-east-1"),
                    "compliance_frameworks": json.dumps(["NIST IR-4", "PCI DSS 11.4"]),
                    "tags": json.dumps({"source": "guard_duty", "type": f.get("Type", "")}),
                    "first_seen_at": f.get("CreatedAt", now()),
                    "last_seen_at": f.get("UpdatedAt", now()),
                    "resolved_at": None,
                    "created_at": now(),
                    "updated_at": now(),
                }
                result = upsert_finding(con, finding)
                if result == "inserted": inserted += 1
                else: updated += 1

        con.commit()
        print(f"    GuardDuty: inserted={inserted}, updated={updated}")
    except ClientError as e:
        print(f"    GuardDuty not available: {e.response['Error']['Code']}")


# ── AWS Config ────────────────────────────────────────────────────────────────

def ingest_config(con):
    print("  Ingesting AWS Config findings...")
    try:
        cfg = client("config")
        paginator = cfg.get_paginator("describe_compliance_by_resource")
        ws_id = strip(WORKSPACE_ID)
        acct_id = strip(PROD_ACCOUNT_UUID)
        inserted = updated = 0

        for page in paginator.paginate(ComplianceTypes=["NON_COMPLIANT"]):
            for res in page.get("ComplianceByResources", []):
                res_type = res.get("ResourceType", "Other")
                res_id   = res.get("ResourceId", "")
                res_arn  = f"arn:aws:config:us-east-1:123456789012:{res_type}/{res_id}"
                fp = fingerprint("config", res_arn, "config-noncompliant")

                finding = {
                    "id": uid(),
                    "workspace_id": ws_id,
                    "aws_account_id": acct_id,
                    "fingerprint": fp,
                    "primary_source": "config",
                    "severity": "medium",
                    "status": "open",
                    "risk_score": 5.0,
                    "title": f"AWS Config Non-Compliant: {res_type} {res_id}",
                    "description": f"AWS Config rule reports {res_type} resource {res_id} as NON_COMPLIANT.",
                    "remediation": "Review the AWS Config console for specific rule violations and apply recommended remediation.",
                    "resource_arn": res_arn,
                    "resource_type": res_type,
                    "region": "us-east-1",
                    "compliance_frameworks": json.dumps(["CIS 2.1.1"]),
                    "tags": json.dumps({"source": "config"}),
                    "first_seen_at": now(),
                    "last_seen_at": now(),
                    "resolved_at": None,
                    "created_at": now(),
                    "updated_at": now(),
                }
                result = upsert_finding(con, finding)
                if result == "inserted": inserted += 1
                else: updated += 1

        con.commit()
        print(f"    AWS Config: inserted={inserted}, updated={updated}")
    except ClientError as e:
        print(f"    AWS Config not available: {e.response['Error']['Code']}")


# ── IAM Access Analyzer ───────────────────────────────────────────────────────

def ingest_access_analyzer(con):
    print("  Ingesting IAM Access Analyzer findings...")
    try:
        aa = client("accessanalyzer")
        analyzers = aa.list_analyzers().get("analyzers", [])
        if not analyzers:
            print("    No IAM Access Analyzer analyzers configured in LocalStack")
            return

        ws_id = strip(WORKSPACE_ID)
        acct_id = strip(PROD_ACCOUNT_UUID)
        inserted = updated = 0

        for analyzer in analyzers:
            paginator = aa.get_paginator("list_findings")
            for page in paginator.paginate(analyzerArn=analyzer["arn"],
                                           filter={"status": {"eq": ["ACTIVE"]}}):
                for f in page.get("findings", []):
                    condition_count = len(f.get("condition", {}))
                    sev = "high" if condition_count == 0 else "medium"
                    res_arn = f.get("resource", "")
                    res_type = f.get("resourceType", "Other")
                    fp = fingerprint("iam_access_analyzer", res_arn, f.get("id", ""))

                    finding = {
                        "id": uid(),
                        "workspace_id": ws_id,
                        "aws_account_id": acct_id,
                        "fingerprint": fp,
                        "primary_source": "iam_access_analyzer",
                        "severity": sev,
                        "status": "open",
                        "risk_score": 7.5 if sev == "high" else 5.0,
                        "title": f"IAM Access Analyzer: External Access to {res_type}",
                        "description": f"IAM Access Analyzer found external access to {res_arn}.",
                        "remediation": "Review IAM Access Analyzer finding and remove unintended external access.",
                        "resource_arn": res_arn,
                        "resource_type": res_type,
                        "region": f.get("region", "us-east-1"),
                        "compliance_frameworks": json.dumps(["CIS 1.16", "NIST AC-3"]),
                        "tags": json.dumps({"source": "iam_access_analyzer"}),
                        "first_seen_at": str(f.get("createdAt", now())),
                        "last_seen_at": str(f.get("updatedAt", now())),
                        "resolved_at": None,
                        "created_at": now(),
                        "updated_at": now(),
                    }
                    result = upsert_finding(con, finding)
                    if result == "inserted": inserted += 1
                    else: updated += 1

        con.commit()
        print(f"    IAM Access Analyzer: inserted={inserted}, updated={updated}")
    except ClientError as e:
        print(f"    IAM Access Analyzer not available: {e.response['Error']['Code']}")


def check_localstack():
    import urllib.request
    try:
        urllib.request.urlopen("http://localhost:4566/_localstack/health", timeout=5)
        return True
    except Exception:
        return False


def main():
    print("=" * 60)
    print("  Cloud Posture — LocalStack Ingestion Script")
    print(f"  DB: {DB_PATH}")
    print("=" * 60)

    if not check_localstack():
        print()
        print("ERROR: LocalStack is not running at http://localhost:4566")
        print("Start it with: docker-compose -f docker-compose.localstack.yml up -d")
        print()
        print("To seed demo data without LocalStack, run seed_full_database.py instead.")
        sys.exit(1)

    print()
    print("LocalStack is available. Connecting to database...")
    con = connect_db()

    try:
        ingest_security_hub(con)
        ingest_guardduty(con)
        ingest_config(con)
        ingest_access_analyzer(con)

        # Print summary
        ws_id = strip(WORKSPACE_ID)
        total = con.execute(
            "SELECT COUNT(*) FROM canonical_findings WHERE workspace_id=?", (ws_id,)
        ).fetchone()[0]
        print()
        print(f"Total findings in database: {total}")
        print("Ingestion complete.")
    except Exception as e:
        con.rollback()
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        con.close()


if __name__ == "__main__":
    main()
