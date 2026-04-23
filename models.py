"""
Shared data models for the Deadlock Detection Tool.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class NodeType(Enum):
    PROCESS = "process"
    RESOURCE = "resource"


class EdgeType(Enum):
    HOLDS = "holds"       # process -> resource
    WAITS_FOR = "waits_for"  # process -> resource (waiting)


class ProcessStatus(Enum):
    RUNNING = "running"
    WAITING = "waiting"
    DEADLOCKED = "deadlocked"


@dataclass
class Process:
    pid: int
    name: str
    status: ProcessStatus = ProcessStatus.RUNNING
    priority: int = 5  # 1 (low) to 10 (high)

    def __hash__(self):
        return hash(self.pid)

    def __eq__(self, other):
        return isinstance(other, Process) and self.pid == other.pid

    def __repr__(self):
        return f"Process(pid={self.pid}, name={self.name})"


@dataclass
class Resource:
    rid: str
    name: str
    held_by: Optional[int] = None   # PID of holder
    waited_by: list = field(default_factory=list)  # PIDs waiting

    def __hash__(self):
        return hash(self.rid)

    def __eq__(self, other):
        return isinstance(other, Resource) and self.rid == other.rid

    def __repr__(self):
        return f"Resource(rid={self.rid}, name={self.name})"


@dataclass
class DeadlockReport:
    cycle: list          # List of node IDs forming the cycle
    involved_processes: list   # Process objects
    involved_resources: list   # Resource objects
    resolution_strategies: list  # List of strategy dicts
    timestamp: str = ""
