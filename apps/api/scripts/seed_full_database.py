#!/usr/bin/env python3
"""
Cloud Posture — Full Database Seeder
Connects directly to demo.db, clears existing synthetic data, and inserts
all 500+ findings, 80+ graph nodes, 120+ edges, 8 attack paths, and
intelligence records.
"""
import sys
import os
import sqlite3
import uuid
import json
from datetime import datetime

# Allow importing from sibling scripts directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from generate_synthetic_data import (
    get_all_data,
    WORKSPACE_ID, PROD_ACCOUNT_UUID, DEV_ACCOUNT_UUID, SEC_ACCOUNT_UUID,
    PROD_ACCOUNT_ID, DEV_ACCOUNT_ID, SEC_ACCOUNT_ID,
    days_ago, strip,
)

DB_PATH = os.path.join(os.path.dirname(SCRIPT_DIR), "demo.db")


def connect():
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=OFF")
    return con


def ensure_workspace(con):
    ws_id = strip(WORKSPACE_ID)
    cur = con.execute("SELECT id FROM workspaces WHERE id = ?", (ws_id,))
    if cur.fetchone():
        print(f"  Workspace already exists: {WORKSPACE_ID}")
        return
    # Get tenant_id from existing workspace
    cur2 = con.execute("SELECT tenant_id FROM workspaces LIMIT 1")
    row = cur2.fetchone()
    tenant_id = row[0] if row else str(uuid.uuid4()).replace("-", "")
    con.execute(
        """INSERT INTO workspaces
           (id, tenant_id, name, slug, status, is_active, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (ws_id, tenant_id, "Cloud Posture Demo", "demo", "active", 1, days_ago(90), days_ago(1)),
    )
    print(f"  Workspace created: {WORKSPACE_ID}")


def ensure_aws_accounts(con):
    accounts = [
        (PROD_ACCOUNT_UUID, WORKSPACE_ID, PROD_ACCOUNT_ID, "prod-account",
         f"arn:aws:iam::{PROD_ACCOUNT_ID}:role/CloudPostureAuditRole", "us-east-1"),
        (DEV_ACCOUNT_UUID,  WORKSPACE_ID, DEV_ACCOUNT_ID,  "dev-account",
         f"arn:aws:iam::{DEV_ACCOUNT_ID}:role/CloudPostureAuditRole",  "us-west-2"),
        (SEC_ACCOUNT_UUID,  WORKSPACE_ID, SEC_ACCOUNT_ID,  "security-account",
         f"arn:aws:iam::{SEC_ACCOUNT_ID}:role/CloudPostureAuditRole",  "us-east-1"),
    ]
    for acct_uuid, ws_uuid, acct_id, alias, role_arn, region in accounts:
        acct_id_stripped = strip(acct_uuid)
        ws_id_stripped   = strip(ws_uuid)
        cur = con.execute("SELECT id FROM aws_accounts WHERE id = ?", (acct_id_stripped,))
        if cur.fetchone():
            print(f"  AWS account already exists: {acct_id} ({alias})")
            continue
        con.execute(
            """INSERT INTO aws_accounts
               (id, workspace_id, account_id, account_alias, role_arn, status,
                enabled_regions, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                acct_id_stripped, ws_id_stripped, acct_id, alias, role_arn, "active",
                json.dumps([region]),
                days_ago(90), days_ago(1),
            ),
        )
        print(f"  AWS account created: {acct_id} ({alias})")


def clear_synthetic_data(con):
    print("  Clearing existing synthetic data...")
    tables = [
        "finding_intelligence",
        "attack_paths",
        "security_graph_edges",
        "security_graph_nodes",
        "canonical_findings",
    ]
    ws_id = strip(WORKSPACE_ID)
    for t in tables:
        cur = con.execute(f"DELETE FROM {t} WHERE workspace_id = ?", (ws_id,))
        print(f"    {t}: deleted {cur.rowcount} rows")


def insert_findings(con, findings):
    print(f"  Inserting {len(findings)} findings...")
    sql = """
        INSERT OR IGNORE INTO canonical_findings
        (id, workspace_id, aws_account_id, fingerprint, primary_source, severity,
         status, risk_score, title, description, remediation, resource_arn,
         resource_type, region, compliance_frameworks, tags,
         first_seen_at, last_seen_at, resolved_at, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """
    rows = [
        (
            f["id"], f["workspace_id"], f["aws_account_id"], f["fingerprint"],
            f["primary_source"], f["severity"], f["status"], f["risk_score"],
            f["title"], f["description"], f["remediation"], f["resource_arn"],
            f["resource_type"], f["region"], f["compliance_frameworks"], f["tags"],
            f["first_seen_at"], f["last_seen_at"], f.get("resolved_at"),
            f["created_at"], f["updated_at"],
        )
        for f in findings
    ]
    con.executemany(sql, rows)
    print(f"    OK: {len(rows)} findings queued")


def insert_nodes(con, nodes):
    print(f"  Inserting {len(nodes)} graph nodes...")
    sql = """
        INSERT OR IGNORE INTO security_graph_nodes
        (id, workspace_id, aws_account_id, node_type, resource_arn, resource_name,
         region, metadata, finding_ids, risk_score, is_internet_facing,
         is_sensitive_data, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """
    rows = [
        (
            n["id"], n["workspace_id"], n.get("aws_account_id", ""),
            n["node_type"], n["resource_arn"], n["resource_name"],
            n["region"], n["metadata"], n["finding_ids"],
            n["risk_score"], n["is_internet_facing"], n["is_sensitive_data"],
            n["created_at"], n["updated_at"],
        )
        for n in nodes
    ]
    con.executemany(sql, rows)
    print(f"    OK: {len(rows)} nodes queued")


def insert_edges(con, edges):
    print(f"  Inserting {len(edges)} graph edges...")
    sql = """
        INSERT OR IGNORE INTO security_graph_edges
        (id, workspace_id, source_node_id, target_node_id, edge_type,
         is_attack_path, risk_contribution, metadata, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """
    rows = [
        (
            e["id"], e["workspace_id"], e["source_node_id"], e["target_node_id"],
            e["edge_type"], e["is_attack_path"], e["risk_contribution"],
            e["metadata"], e["created_at"], e["updated_at"],
        )
        for e in edges
    ]
    con.executemany(sql, rows)
    print(f"    OK: {len(rows)} edges queued")


def insert_attack_paths(con, paths):
    print(f"  Inserting {len(paths)} attack paths...")
    sql = """
        INSERT OR IGNORE INTO attack_paths
        (id, workspace_id, name, description, severity, node_path, edge_path,
         toxic_combo_tags, blast_radius, entry_node_id, target_node_id,
         entry_description, target_description, is_active, related_finding_ids,
         created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """
    rows = [
        (
            p["id"], p["workspace_id"], p["name"], p["description"], p["severity"],
            p["node_path"], p["edge_path"], p["toxic_combo_tags"], p["blast_radius"],
            p.get("entry_node_id"), p.get("target_node_id"),
            p.get("entry_description"), p.get("target_description"),
            p["is_active"], p["related_finding_ids"],
            p["created_at"], p["updated_at"],
        )
        for p in paths
    ]
    con.executemany(sql, rows)
    print(f"    OK: {len(rows)} attack paths queued")


def insert_intelligence(con, records):
    print(f"  Inserting {len(records)} intelligence records...")
    sql = """
        INSERT OR IGNORE INTO finding_intelligence
        (id, workspace_id, finding_id, what_is_it, current_state, expected_state,
         business_impact, attack_scenario, composite_score, primary_root_cause,
         causal_factors, causal_chain, toxic_combinations, blast_radius_count,
         confidence, rag_level, rag_composite_score, rag_primary_reason,
         sla_days, escalation_required, stakeholders,
         immediate_actions, sprint_actions, quarterly_actions,
         ollama_model, fallback_used, generation_status, error_message,
         created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """
    rows = [
        (
            r["id"], r["workspace_id"], r["finding_id"],
            r["what_is_it"], r["current_state"], r["expected_state"],
            r["business_impact"], r["attack_scenario"], r["composite_score"],
            r["primary_root_cause"], r["causal_factors"], r["causal_chain"],
            r["toxic_combinations"], r["blast_radius_count"], r["confidence"],
            r["rag_level"], r["rag_composite_score"], r["rag_primary_reason"],
            r["sla_days"], r["escalation_required"], r["stakeholders"],
            r["immediate_actions"], r["sprint_actions"], r["quarterly_actions"],
            r["ollama_model"], r["fallback_used"], r["generation_status"],
            r.get("error_message"), r["created_at"], r["updated_at"],
        )
        for r in records
    ]
    con.executemany(sql, rows)
    print(f"    OK: {len(rows)} intelligence records queued")


def print_summary(con):
    print()
    print("=" * 60)
    print("  DATABASE SUMMARY")
    print("=" * 60)

    ws_id = strip(WORKSPACE_ID)

    counts = {}
    for table in ["canonical_findings", "security_graph_nodes",
                  "security_graph_edges", "attack_paths", "finding_intelligence"]:
        cur = con.execute(f"SELECT COUNT(*) FROM {table} WHERE workspace_id=?", (ws_id,))
        counts[table] = cur.fetchone()[0]

    print(f"  Findings          : {counts['canonical_findings']}")
    print(f"  Graph Nodes       : {counts['security_graph_nodes']}")
    print(f"  Graph Edges       : {counts['security_graph_edges']}")
    print(f"  Attack Paths      : {counts['attack_paths']}")
    print(f"  Intelligence Rec. : {counts['finding_intelligence']}")

    # Severity distribution
    print()
    print("  Severity Distribution:")
    for sev in ["critical", "high", "medium", "low", "informational"]:
        cur = con.execute(
            "SELECT COUNT(*) FROM canonical_findings WHERE workspace_id=? AND severity=?",
            (ws_id, sev)
        )
        cnt = cur.fetchone()[0]
        bar = "#" * (cnt // 5)
        print(f"    {sev:15s}: {cnt:4d}  {bar}")

    # Source distribution
    print()
    print("  Source Distribution:")
    for src in ["security_hub", "guard_duty", "inspector", "config", "iam_access_analyzer"]:
        cur = con.execute(
            "SELECT COUNT(*) FROM canonical_findings WHERE workspace_id=? AND primary_source=?",
            (ws_id, src)
        )
        cnt = cur.fetchone()[0]
        print(f"    {src:25s}: {cnt:4d}")

    # RAG distribution
    print()
    print("  RAG Distribution (from intelligence records):")
    for rag in ["RED", "AMBER", "GREEN"]:
        cur = con.execute(
            "SELECT COUNT(*) FROM finding_intelligence WHERE workspace_id=? AND rag_level=?",
            (ws_id, rag)
        )
        cnt = cur.fetchone()[0]
        print(f"    {rag:8s}: {cnt:4d}")

    # Top 5 RED findings
    print()
    print("  Top 5 RED Findings by Risk Score:")
    cur = con.execute(
        """SELECT cf.title, cf.severity, cf.risk_score, cf.primary_source
           FROM canonical_findings cf
           JOIN finding_intelligence fi ON cf.id = fi.finding_id
           WHERE cf.workspace_id=? AND fi.rag_level='RED'
           ORDER BY cf.risk_score DESC LIMIT 5""",
        (ws_id,)
    )
    for i, row in enumerate(cur.fetchall(), 1):
        title, sev, score, src = row
        print(f"    {i}. [{score:.1f}] {title[:65]}")
        print(f"       {sev.upper()} | {src}")

    # Attack paths
    print()
    print("  Attack Paths:")
    cur = con.execute(
        "SELECT name, severity, blast_radius FROM attack_paths WHERE workspace_id=? ORDER BY blast_radius DESC",
        (ws_id,)
    )
    for row in cur.fetchall():
        name, sev, blast = row
        print(f"    [{sev.upper():8s}] {name[:60]}  (blast={blast})")

    print()
    print("  Seeding complete.")
    print("=" * 60)


def main():
    print("=" * 60)
    print("  Cloud Posture — Full Database Seeder")
    print(f"  DB: {DB_PATH}")
    print("=" * 60)

    if not os.path.exists(DB_PATH):
        print(f"ERROR: demo.db not found at {DB_PATH}")
        sys.exit(1)

    print()
    print("Generating synthetic data...")
    findings, nodes, edges, attack_paths, intelligence = get_all_data()
    print(f"  Generated: {len(findings)} findings, {len(nodes)} nodes, "
          f"{len(edges)} edges, {len(attack_paths)} paths, {len(intelligence)} intel records")

    print()
    print("Connecting to database...")
    con = connect()

    try:
        ensure_workspace(con)
        ensure_aws_accounts(con)
        clear_synthetic_data(con)
        print()
        insert_findings(con, findings)
        insert_nodes(con, nodes)
        insert_edges(con, edges)
        insert_attack_paths(con, attack_paths)
        insert_intelligence(con, intelligence)
        con.commit()
        print()
        print("All inserts committed.")
        print_summary(con)
    except Exception as e:
        con.rollback()
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        con.close()


if __name__ == "__main__":
    main()
