"""
Neo4j client — graph database integration for OmniSec security graph.

Sprint 31: Provides async Neo4j driver, session management, and health check.
Uses neo4j async driver (neo4j[async]).
"""

import os
from typing import Any
from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession

_driver: AsyncDriver | None = None


async def get_neo4j_driver() -> AsyncDriver:
    """Get or create the Neo4j async driver singleton."""
    global _driver
    if _driver is None:
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        _driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    return _driver


async def get_neo4j_session() -> AsyncSession:
    """Get a new Neo4j async session."""
    driver = await get_neo4j_driver()
    return driver.session()


async def close_neo4j():
    """Close the Neo4j driver on shutdown."""
    global _driver
    if _driver:
        await _driver.close()
        _driver = None


async def neo4j_health() -> dict:
    """Health check for Neo4j connection."""
    try:
        driver = await get_neo4j_driver()
        async with driver.session() as session:
            result = await session.run("RETURN 1 AS ok")
            record = await result.single()
            return {"status": "ok", "connected": True, "value": record["ok"]}
    except Exception as e:
        return {"status": "error", "connected": False, "error": str(e)}
