"""virtuoso-bridge – Python bridge for executing SKILL in Cadence Virtuoso."""

from virtuoso_bridge.virtuoso.basic.bridge import VirtuosoClient
from virtuoso_bridge.virtuoso.basic.client import BridgeClient
from virtuoso_bridge.virtuoso.basic.service import BridgeService
from virtuoso_bridge.transport.tunnel import SSHClient
from virtuoso_bridge.virtuoso.basic.runtime_status import (
    collect_runtime_status,
    format_runtime_status,
)
from virtuoso_bridge.models import (
    ExecutionStatus,
    SimulationResult,
    SkillResult,
    VirtuosoResult,
)
from virtuoso_bridge.spectre.runner import SpectreSimulator

# Backward compatibility
RAMICBridge = VirtuosoClient
TunnelService = SSHClient

__all__ = [
    "VirtuosoClient",
    "SSHClient",
    "BridgeClient",
    "BridgeService",
    "RAMICBridge",      # deprecated alias
    "TunnelService",    # deprecated alias
    "VirtuosoResult",
    "ExecutionStatus",
    "SkillResult",
    "collect_runtime_status",
    "format_runtime_status",
    "SpectreSimulator",
    "SimulationResult",
]
