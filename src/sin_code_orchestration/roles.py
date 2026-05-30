"""Rollen-Definitionen für Agenten im Orchestrierungs-System."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Role(str, Enum):
    PLANNER = "planner"
    CODER = "coder"
    REVIEWER = "reviewer"
    VERIFIER = "verifier"
    DEPLOYER = "deployer"
    MONITOR = "monitor"


@dataclass
class ToolPermission:
    """Erlaubte Tools und ihre Parameter-Beschränkungen."""
    name: str
    read_only: bool = False
    max_output_tokens: Optional[int] = None
    allowed_patterns: list[str] = field(default_factory=list)


@dataclass
class AgentConfig:
    """Konfiguration eines Agenten mit Rolle und Berechtigungen."""
    agent_id: str
    role: Role
    model: str
    tools: list[ToolPermission] = field(default_factory=list)
    max_iterations: int = 10
    timeout_seconds: int = 300
    sandbox: bool = False
    require_approval: bool = False
    escalation_path: Optional[str] = None

    def can_use_tool(self, tool_name: str, write_operation: bool = False) -> bool:
        for tool in self.tools:
            if tool.name == tool_name:
                if write_operation and tool.read_only:
                    return False
                return True
        return False

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "model": self.model,
            "tools": [t.name for t in self.tools],
            "max_iterations": self.max_iterations,
            "timeout_seconds": self.timeout_seconds,
        }
