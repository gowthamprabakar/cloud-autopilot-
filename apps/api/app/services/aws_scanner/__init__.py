"""
AWS Scanner package — ingests findings from AWS security services.

Public API:
    IngestionEngine — orchestrates all scanners for a workspace/account.
"""

from app.services.aws_scanner.ingestion_engine import IngestionEngine

__all__ = ["IngestionEngine"]
