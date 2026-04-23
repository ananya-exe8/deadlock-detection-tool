"""
Module 2: Detection Engine
--------------------------
Analyses the Resource Allocation Graph (RAG) to:
  1. Build the Wait-For Graph (WFG)
  2. Detect cycles  (deadlocks)
  3. Score & rank resolution strategies
  4. Identify near-deadlock (at-risk) states

Uses NetworkX's built-in DFS-based cycle finder + Tarjan's SCC algorithm
for multi-resource scenarios.
"""

import networkx as nx
from datetime import datetime
from models import (
    Process, Resource, NodeType, EdgeType,
    ProcessStatus, DeadlockReport,
)
from ingestion import get_wait_for_graph


# ---------------------------------------------------------------------------
# Cycle detection helpers
# ---------------------------------------------------------------------------

def find_all_cycles(G: nx.DiGraph) -> list[list]:
    """
    Return all simple cycles in a directed graph using Johnson's algorithm
    (via networkx.simple_cycles).  Each cycle is a list of node IDs.
    """
    return list(nx.simple_cycles(G))


def find_deadlock_cycles_in_rag(G: nx.DiGraph) -> list[list]:
    """
    Detect deadlocks in the RAG by building a process-only wait-for graph
    and finding cycles there. A cycle in the wait-for graph = deadlock.

    A process P_i waits for P_j if:
      P_i --waits_for--> R  and  P_j --holds--> R
    """
    # Build process-to-process wait-for edges
    WFG = nx.DiGraph()
    proc_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") == NodeType.PROCESS]
    WFG.add_nodes_from(proc_nodes)

    for u, v, ed in G.edges(data=True):
        if ed.get("edge_type") == EdgeType.WAITS_FOR:
            # u (process) waits for resource v
            # find who holds v
            for holder, res, he in G.edges(data=True):
                if res == v and he.get("edge_type") == EdgeType.HOLDS and holder != u:
                    WFG.add_edge(u, holder, resource=v)

    cycles = list(nx.simple_cycles(WFG))
    # Map back to RAG node IDs (they're already process node IDs)
    return cycles


def detect_via_wait_for_graph(G: nx.DiGraph) -> list[list]:
    """
    Build WFG and find cycles in it (Coffman's circular-wait condition).
    Returns cycles as lists of process node IDs.
    """
    WFG = get_wait_for_graph(G)
    return find_all_cycles(WFG)


def is_deadlocked(G: nx.DiGraph) -> bool:
    """Quick boolean check."""
    return len(find_deadlock_cycles_in_rag(G)) > 0


# ---------------------------------------------------------------------------
# Near-deadlock detection
# ---------------------------------------------------------------------------

def find_near_deadlock_processes(G: nx.DiGraph) -> list[str]:
    """
    Identify processes that are one resource acquisition away from
    causing a deadlock.  Returns list of process node IDs at risk.
    """
    at_risk = []
    # Check: if any waiting process already holds resources that
    # a different waiting process needs, flag it
    waiting_procs = [
        n for n, d in G.nodes(data=True)
        if d.get("node_type") == NodeType.PROCESS
        and d.get("data") and d["data"].status == ProcessStatus.WAITING
    ]

    for proc_node in waiting_procs:
        # What does this process hold?
        holds = [v for (u, v, ed) in G.edges(data=True)
                 if u == proc_node and ed.get("edge_type") == EdgeType.HOLDS]
        # What does it wait for?
        waits = [v for (u, v, ed) in G.edges(data=True)
                 if u == proc_node and ed.get("edge_type") == EdgeType.WAITS_FOR]

        if holds and waits:
            at_risk.append(proc_node)

    return at_risk


# ---------------------------------------------------------------------------
# Resolution strategies
# ---------------------------------------------------------------------------

def _score_victim(proc_node: str, G: nx.DiGraph) -> float:
    """
    Score a process as a termination victim.
    Lower score = better candidate for termination.
    Factors: priority (lower is cheaper to kill), resources held (fewer is cheaper).
    """
    data = G.nodes[proc_node].get("data")
    if not isinstance(data, Process):
        return 999.0

    held_count = sum(
        1 for (u, v, ed) in G.edges(data=True)
        if u == proc_node and ed.get("edge_type") == EdgeType.HOLDS
    )
    # Lower priority + fewer resources held = lower score = better victim
    score = (data.priority * 2) + (held_count * 3)
    return score


def generate_resolution_strategies(
    cycle: list, G: nx.DiGraph, involved_resources: list = None
) -> list[dict]:
    """
    Given a deadlock cycle (list of process node IDs), generate ranked strategies.
    Returns list of dicts with keys: rank, action, target, description, impact.
    """
    strategies = []
    if involved_resources is None:
        involved_resources = []

    proc_nodes = [n for n in cycle if G.nodes.get(n, {}).get("node_type") == NodeType.PROCESS]
    res_labels = [r.name for r in involved_resources] if involved_resources else []

    # Strategy 1: Terminate lowest-priority process
    if proc_nodes:
        victims = sorted(proc_nodes, key=lambda n: _score_victim(n, G))
        best_victim = victims[0]
        victim_data = G.nodes[best_victim].get("data")
        strategies.append({
            "rank": 1,
            "action": "Terminate Process",
            "target": best_victim,
            "target_label": G.nodes[best_victim].get("label", best_victim),
            "description": (
                f"Terminate {victim_data.name} (PID {victim_data.pid}). "
                f"It holds the fewest resources and has the lowest priority "
                f"(priority={victim_data.priority}). "
                f"Its resources will be released and re-allocated to waiting processes."
            ),
            "impact": "Medium — process must restart; possible data rollback required.",
        })

    # Strategy 2: Preempt a resource from highest-priority holder
    if involved_resources and proc_nodes:
        holders = sorted(proc_nodes, key=lambda n: _score_victim(n, G), reverse=True)
        preempt_proc = holders[0]
        preempt_data = G.nodes[preempt_proc].get("data")
        held_res = [
            v for (u, v, ed) in G.edges(data=True)
            if u == preempt_proc and ed.get("edge_type") == EdgeType.HOLDS
        ]
        if held_res:
            res_label = G.nodes[held_res[0]].get("label", held_res[0])
            strategies.append({
                "rank": 2,
                "action": "Preempt Resource",
                "target": held_res[0],
                "target_label": res_label,
                "description": (
                    f"Forcibly revoke {res_label} "
                    f"from {preempt_data.name} (PID {preempt_data.pid}). "
                    f"Grant it to the next waiting process. "
                    f"{preempt_data.name} will need to re-acquire later."
                ),
                "impact": "Low — process continues but may retry resource acquisition.",
            })

    # Strategy 3: Resource ordering / lock hierarchy (preventive)
    res_order = " -> ".join(res_labels) if res_labels else "R1 -> R2 -> ..."
    strategies.append({
        "rank": 3,
        "action": "Enforce Lock Ordering",
        "target": "system",
        "target_label": "System Policy",
        "description": (
            f"Impose a global resource acquisition order: {res_order}. "
            "All processes must request resources in this order to prevent future cycles."
        ),
        "impact": "High — permanent fix; requires code changes in all affected processes.",
    })

    # Strategy 4: Add timeout + retry (softer)
    strategies.append({
        "rank": 4,
        "action": "Add Acquisition Timeout",
        "target": "system",
        "target_label": "System Policy",
        "description": (
            "Set a maximum wait time (e.g., 5 seconds) on all resource acquisition calls. "
            "If a process cannot acquire a resource within the timeout, it releases all "
            "currently held resources and retries after a random backoff interval."
        ),
        "impact": "Low — no termination; may add latency under contention.",
    })

    return strategies


# ---------------------------------------------------------------------------
# High-level API
# ---------------------------------------------------------------------------

class DetectionEngine:
    """High-level API for the detection module."""

    def __init__(self, G: nx.DiGraph):
        self.G = G
        self._report: DeadlockReport | None = None

    def run(self) -> DeadlockReport | None:
        """
        Full analysis pass.  Returns a DeadlockReport if deadlock found, else None.
        Updates process node statuses to DEADLOCKED where appropriate.
        """
        cycles = find_deadlock_cycles_in_rag(self.G)

        if not cycles:
            self._report = None
            return None

        # Use the first (usually smallest) cycle for the report
        primary_cycle = cycles[0]

        # primary_cycle is a list of process node IDs (e.g. ["P101", "P102"])
        # Mark deadlocked processes
        for node in primary_cycle:
            proc = self.G.nodes.get(node, {}).get("data")
            if isinstance(proc, Process):
                proc.status = ProcessStatus.DEADLOCKED

        involved_processes = [
            self.G.nodes[n]["data"] for n in primary_cycle
            if isinstance(self.G.nodes[n].get("data"), Process)
        ]

        # Find resources involved: those waited-for or held within the cycle processes
        involved_resource_nodes = set()
        for pnode in primary_cycle:
            for u, v, ed in self.G.edges(pnode, data=True):
                if self.G.nodes[v].get("node_type") == NodeType.RESOURCE:
                    involved_resource_nodes.add(v)

        involved_resources = [
            self.G.nodes[rn]["data"] for rn in involved_resource_nodes
            if self.G.nodes[rn].get("data") is not None
        ]

        strategies = generate_resolution_strategies(primary_cycle, self.G, involved_resources)

        self._report = DeadlockReport(
            cycle=primary_cycle,
            involved_processes=involved_processes,
            involved_resources=involved_resources,
            resolution_strategies=strategies,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        return self._report

    def near_deadlock_nodes(self) -> list[str]:
        return find_near_deadlock_processes(self.G)

    def all_cycles(self) -> list[list]:
        return find_deadlock_cycles_in_rag(self.G)

    @property
    def report(self):
        return self._report

    def print_report(self):
        if not self._report:
            print("No deadlock detected.")
            return
        r = self._report
        print(f"\n{'='*60}")
        print(f"  DEADLOCK DETECTED  —  {r.timestamp}")
        print(f"{'='*60}")
        print(f"Cycle: {' -> '.join(r.cycle)} -> {r.cycle[0]}")
        print(f"\nInvolved Processes:")
        for p in r.involved_processes:
            print(f"  • {p.name} (PID {p.pid}, priority={p.priority})")
        print(f"\nInvolved Resources:")
        for res in r.involved_resources:
            print(f"  • {res.name} [{res.rid}]")
        print(f"\nResolution Strategies (ranked):")
        for s in r.resolution_strategies:
            print(f"  [{s['rank']}] {s['action']} — {s['target_label']}")
            print(f"       {s['description']}")
            print(f"       Impact: {s['impact']}")
        print(f"{'='*60}\n")
