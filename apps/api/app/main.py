"""
Cloud Posture Copilot — FastAPI application entrypoint.

Phase 1: auth + tenant foundation + workspaces.
Future sprints add routers incrementally per the phased build plan.
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.core.logging import configure_logging
from app.routers import ai, agent, api_keys, attack_paths, audit_log, auth, aws_accounts, ciem, compliance, detections, domains, drift, email_digest, executive, findings, graph, health, infra_health, intelligence, memory, notifications, portfolio, prompt_registry, reports, scanner, simulations, suppression, totp, users, vulns, webhooks, workspaces, workspace_settings, sla, jira, onboarding, security_graph

configure_logging()
logger = structlog.get_logger(__name__)

scheduler = AsyncIOScheduler()


async def run_scheduled_reports():
    """Hourly check — send digests for workspaces whose schedule is due."""
    from datetime import datetime, UTC
    from app.core.database import AsyncSessionLocal
    from app.repositories.report_schedule_repository import ReportScheduleRepository
    from app.services.digest_service import DigestService
    import json
    import logging

    _logger = logging.getLogger(__name__)
    try:
        async with AsyncSessionLocal() as db:
            repo = ReportScheduleRepository(db)
            schedules = await repo.get_all_enabled()
            now = datetime.now(UTC)
            for schedule in schedules:
                # Check if it's time to send (weekly: check day_of_week; monthly: check day 1)
                should_send = False
                if schedule.frequency == "weekly":
                    should_send = now.isoweekday() == schedule.day_of_week
                elif schedule.frequency == "monthly":
                    should_send = now.day == 1

                # Also check not already sent today
                if schedule.last_sent_at:
                    last = schedule.last_sent_at
                    if hasattr(last, 'tzinfo') and last.tzinfo is None:
                        last = last.replace(tzinfo=UTC)
                    if (now - last).days < 1:
                        should_send = False

                if should_send:
                    recipients = []
                    if schedule.recipients:
                        try:
                            recipients = json.loads(schedule.recipients)
                        except Exception:
                            recipients = []
                    if recipients:
                        svc = DigestService(db)
                        sent = await svc.send_digest(schedule.workspace_id, recipients)
                        await repo.mark_sent(schedule.id)
                        _logger.info(f"Scheduled digest sent workspace={schedule.workspace_id} sent={sent}")
    except Exception as e:
        _logger.error(f"run_scheduled_reports error: {e}")


async def run_scheduled_aws_scan():
    """Runs every 15 min — scans all workspaces that have connected AWS accounts."""
    import logging
    from app.core.database import AsyncSessionLocal
    from app.services.aws_scanner import IngestionEngine
    from app.models.aws_account import AwsAccount
    from app.models.workspace import Workspace
    from sqlalchemy import select

    _logger = logging.getLogger(__name__)
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Workspace.id))
            workspace_ids = [str(row[0]) for row in result.fetchall()]
            for ws_id in workspace_ids:
                engine = IngestionEngine(db, ws_id)
                scan_result = await engine.run_full_scan(triggered_by="scheduler")
                _logger.info(
                    "Scheduled scan workspace=%s added=%d updated=%d status=%s",
                    ws_id, scan_result.findings_added, scan_result.findings_updated, scan_result.status,
                )
    except Exception as exc:
        logging.getLogger(__name__).error("run_scheduled_aws_scan error: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail fast if running in production with insecure default secrets.
    settings.assert_production_secrets()
    logger.info(
        "startup",
        env=settings.api_env,
        version="0.2.0-phase2",
    )
    if not scheduler.running:
        scheduler.add_job(run_scheduled_reports, CronTrigger(minute=0))
        # AWS scanner — runs every 15 minutes for all workspaces
        scheduler.add_job(
            run_scheduled_aws_scan,
            "interval",
            minutes=15,
            id="aws_scanner",
            replace_existing=True,
        )
        scheduler.start()
    yield
    if scheduler.running:
        scheduler.shutdown()
    # Sprint 31 — close Neo4j driver
    from app.core.neo4j_client import close_neo4j
    await close_neo4j()
    logger.info("shutdown")


app = FastAPI(
    title="Cloud Posture Copilot API",
    version="0.0.1",
    description="AWS-native Cloud Security Operations Platform",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────
# Tighten allowed_origins in production via env
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"] if settings.is_development else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Observability ──────────────────────────────────────────────────
from app.middleware.metrics_middleware import MetricsMiddleware
app.add_middleware(MetricsMiddleware)

from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response as FastAPIResponse

@app.get("/metrics", include_in_schema=False)
async def metrics() -> FastAPIResponse:
    """Prometheus metrics endpoint. Protect with network policy in production."""
    return FastAPIResponse(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )

# ── Routers ───────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(workspaces.router, prefix="/api/v1")
app.include_router(aws_accounts.router, prefix="/api/v1")
app.include_router(findings.router, prefix="/api/v1")
app.include_router(compliance.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(audit_log.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(suppression.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(api_keys.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(workspace_settings.router, prefix="/api/v1")
app.include_router(sla.router, prefix="/api/v1")
app.include_router(email_digest.router, prefix="/api/v1")
app.include_router(jira.router, prefix="/api/v1")
app.include_router(onboarding.router, prefix="/api/v1")
app.include_router(totp.router, prefix="/api/v1")
app.include_router(security_graph.router, prefix="/api/v1")
app.include_router(intelligence.router, prefix="/api/v1")
app.include_router(scanner.router, prefix="/api/v1")
# Sprint 18 — THINK layer agents (triage, attack path, audit logs)
app.include_router(agent.router, prefix="/api/v1")
# Sprint 20 — Executive dashboard
app.include_router(executive.router, prefix="/api/v1")
# Sprint 21 — CIEM Foundation
app.include_router(ciem.router, prefix="/api/v1")
# Sprint 22 — Vulnerability Management (CVE + EPSS + KEV)
app.include_router(vulns.router, prefix="/api/v1")
# Sprint 23 — Cloud Detection & Response (CDR)
app.include_router(detections.router, prefix="/api/v1")
# Sprint 24 — MSP Portfolio
app.include_router(portfolio.router, prefix="/api/v1")
# Sprint 26 — AI Prompt Registry
app.include_router(prompt_registry.router, prefix="/api/v1")
# Sprint 27 — Attack Path Visualization
app.include_router(attack_paths.router, prefix="/api/v1")
# Sprint 28 — Drift Detection
app.include_router(drift.router, prefix="/api/v1")
# Sprint 29 — OmniSec Simulation Engine
app.include_router(simulations.router, prefix="/api/v1")
# Sprint 30 — Domains & Agent Spawning
app.include_router(domains.router, prefix="/api/v1")
# Sprint 31 — Neo4j Graph
app.include_router(graph.router, prefix="/api/v1")
# Sprint 31 — Infrastructure Health & Metrics
app.include_router(infra_health.router, prefix="/api/v1")
# Sprint 31 — Agent Memory (Zep-compatible)
app.include_router(memory.router, prefix="/api/v1")

# Phase 4+ will add:
# app.include_router(workflows.router,    prefix="/api/v1")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", path=str(request.url))
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred"},
    )
