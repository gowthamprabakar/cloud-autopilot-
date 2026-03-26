"""
Event Handlers — React to OmniSec events.

Sprint 31: Handlers for simulation lifecycle, agent lifecycle, and gate events.
These handlers perform side effects like updating run counters, logging, and triggering graph syncs.
"""

from app.services.event_bus import Event

async def on_simulation_started(event: Event):
    """Log simulation start, could trigger notifications."""
    pass  # Sprint 31: placeholder for notification integration

async def on_simulation_completed(event: Event):
    """Trigger post-simulation actions: memory learning, graph sync."""
    pass  # Will call memory_service.learn_from_simulation in Sprint 32

async def on_agent_completed(event: Event):
    """Update agent metrics, store working memory snapshot."""
    pass  # Will integrate with memory_service in Sprint 32

async def on_gate_passed(event: Event):
    """Track gate pass for metrics and alerting."""
    pass

async def on_gate_failed(event: Event):
    """Alert on gate failure — could trigger re-evaluation."""
    pass

def register_default_handlers(bus):
    """Register all default event handlers."""
    bus.on("simulation.started", on_simulation_started)
    bus.on("simulation.completed", on_simulation_completed)
    bus.on("agent.completed", on_agent_completed)
    bus.on("gate.passed", on_gate_passed)
    bus.on("gate.failed", on_gate_failed)
