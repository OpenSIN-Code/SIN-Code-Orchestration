"""SIN-Code Advanced Multi-Agent Orchestration."""
__version__ = "0.1.0"

from .orchestrator import Orchestrator, TaskResult
from .ca_mcp import ContextAwareMCP
from .shared_context import SharedContextStore, ContextEntry
from .roles import Role, AgentConfig
from .verifier import VerificationLoop, VerificationResult

__all__ = [
    "Orchestrator",
    "TaskResult",
    "ContextAwareMCP",
    "SharedContextStore",
    "ContextEntry",
    "Role",
    "AgentConfig",
    "VerificationLoop",
    "VerificationResult",
]
