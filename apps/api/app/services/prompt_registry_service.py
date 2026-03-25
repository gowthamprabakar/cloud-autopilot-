"""
PromptRegistryService — AI Prompt Registry (Sprint 26).

Manages versioned prompt templates with workspace-level overrides.
"""
from __future__ import annotations
import uuid
from typing import Any
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.prompt_registry import PromptRegistry


class PromptRegistryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_prompts(self, workspace_id: uuid.UUID | None = None) -> list[dict]:
        """List all active prompts (global + workspace-specific)."""
        # Get global prompts + workspace-specific prompts
        stmt = select(PromptRegistry).where(
            PromptRegistry.is_active == True,
            or_(
                PromptRegistry.workspace_id == None,
                PromptRegistry.workspace_id == workspace_id,
            )
        ).order_by(PromptRegistry.category, PromptRegistry.name, PromptRegistry.version.desc())

        result = await self.db.execute(stmt)
        prompts = list(result.scalars().all())

        return [self._to_dict(p) for p in prompts]

    async def get_prompt(self, name: str, workspace_id: uuid.UUID | None = None) -> dict | None:
        """Get the active prompt by name, preferring workspace-specific over global."""
        # Try workspace-specific first
        if workspace_id:
            stmt = select(PromptRegistry).where(
                PromptRegistry.name == name,
                PromptRegistry.workspace_id == workspace_id,
                PromptRegistry.is_active == True,
            ).order_by(PromptRegistry.version.desc()).limit(1)
            result = await self.db.execute(stmt)
            prompt = result.scalar_one_or_none()
            if prompt:
                return self._to_dict(prompt)

        # Fall back to global
        stmt = select(PromptRegistry).where(
            PromptRegistry.name == name,
            PromptRegistry.workspace_id == None,
            PromptRegistry.is_active == True,
        ).order_by(PromptRegistry.version.desc()).limit(1)
        result = await self.db.execute(stmt)
        prompt = result.scalar_one_or_none()
        return self._to_dict(prompt) if prompt else None

    async def create_prompt(self, data: dict) -> dict:
        """Create a new prompt template."""
        prompt = PromptRegistry(
            workspace_id=data.get("workspace_id"),
            name=data["name"],
            version=data.get("version", 1),
            template=data["template"],
            model_id=data.get("model_id", "bedrock/claude-3-sonnet"),
            category=data.get("category", "general"),
            is_active=data.get("is_active", True),
        )
        self.db.add(prompt)
        await self.db.commit()
        await self.db.refresh(prompt)
        return self._to_dict(prompt)

    async def update_prompt(self, prompt_id: uuid.UUID, data: dict) -> dict | None:
        """Update an existing prompt (creates new version)."""
        stmt = select(PromptRegistry).where(PromptRegistry.id == prompt_id)
        result = await self.db.execute(stmt)
        prompt = result.scalar_one_or_none()
        if not prompt:
            return None

        for key in ["template", "model_id", "category", "is_active"]:
            if key in data:
                setattr(prompt, key, data[key])
        if "template" in data:
            prompt.version = (prompt.version or 1) + 1

        await self.db.commit()
        await self.db.refresh(prompt)
        return self._to_dict(prompt)

    async def seed_defaults(self, workspace_id: uuid.UUID | None = None) -> int:
        """Seed default prompt templates if none exist."""
        existing = await self.list_prompts(workspace_id)
        if existing:
            return 0

        defaults = [
            {"name": "finding_summary", "category": "finding_summary", "template": "Analyze this security finding and provide: 1) A clear summary of the issue 2) Why it matters 3) The likely root cause. Finding: {finding_title}. Description: {finding_description}. Resource: {resource_arn}. Severity: {severity}.", "model_id": "bedrock/claude-3-sonnet"},
            {"name": "remediation_plan", "category": "remediation", "template": "Generate a step-by-step remediation plan for this security finding. Include AWS CLI commands where applicable. Finding: {finding_title}. Resource: {resource_arn}. Resource Type: {resource_type}. Current State: {finding_description}.", "model_id": "bedrock/claude-3-sonnet"},
            {"name": "root_cause_analysis", "category": "root_cause", "template": "Perform root cause analysis on this security finding. Identify: 1) The configuration or policy that caused it 2) Whether this is a systemic issue or isolated 3) Related findings that may share the same root cause. Finding: {finding_title}. Description: {finding_description}.", "model_id": "bedrock/claude-3-sonnet"},
            {"name": "executive_brief", "category": "governance", "template": "Write a 2-3 sentence executive brief for this security finding suitable for a CISO or board report. Avoid technical jargon. Focus on business risk and recommended action. Finding: {finding_title}. Severity: {severity}. Resource: {resource_type}.", "model_id": "bedrock/claude-3-sonnet"},
            {"name": "compliance_impact", "category": "governance", "template": "Assess the compliance impact of this finding against common frameworks (SOC2, ISO 27001, FSBP). Identify which control families are affected. Finding: {finding_title}. Description: {finding_description}. Frameworks: {compliance_frameworks}.", "model_id": "bedrock/claude-3-sonnet"},
        ]

        count = 0
        for d in defaults:
            d["workspace_id"] = workspace_id
            await self.create_prompt(d)
            count += 1
        return count

    def _to_dict(self, p: PromptRegistry) -> dict:
        return {
            "id": str(p.id),
            "workspace_id": str(p.workspace_id) if p.workspace_id else None,
            "name": p.name,
            "version": p.version,
            "template": p.template,
            "model_id": p.model_id,
            "category": p.category,
            "is_active": p.is_active,
            "created_at": p.created_at.isoformat() if hasattr(p.created_at, 'isoformat') else str(p.created_at) if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if hasattr(p.updated_at, 'isoformat') else str(p.updated_at) if p.updated_at else None,
        }
