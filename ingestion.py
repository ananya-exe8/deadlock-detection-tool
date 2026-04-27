"""
Module 1: Data Ingestion
------------------------
Reads process/resource state (live via psutil or simulated) and builds
a Resource Allocation Graph (RAG) as a NetworkX DiGraph.

Nodes:
  - "P<pid>"  -> process node
  - "R<rid>"  -> resource node
Edges:
  - P -> R  with type="holds"
  - P -> R  with type="waits_for"
"""

import time
import random
import networkx as nx

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from models import Process, Resource, NodeType, EdgeType, ProcessStatus


# ---------------------------------------------------------------------------
# OS-based ingestion (requires psutil + elevated permissions on some systems)
# ---------------------------------------------------------------------------

def read_live_processes():
    """
    Attempt to read real process open-file handles via psutil.
    Returns (processes_dict, resources_dict, edges_list).
    Falls back to empty data if permissions are insufficient.
    """
    processes = {}
    resources = {}
    edges = []

    if not PSUTIL_AVAILABLE:
        return processes, resources, edges

    try:
        for proc in psutil.process_iter(['pid', 'name', 'status', 'nice']):
            try:
                info = proc.info
                pid = info['pid']
                name = info['name'] or f"pid_{pid}"
                status = ProcessStatus.RUNNING if info['status'] == 'running' else ProcessStatus.WAITING
                priority = max(1, min(10, 5 - (info.get('nice') or 0) // 4))
                processes[pid] = Process(pid=pid, name=name, status=status, priority=priority)

                # Use open files as "resources"
                try:
                    for f in proc.open_files():
                        rid = f"FILE_{abs(hash(f.path)) % 10000:04d}"
                        rname = f.path.split('/')[-1][:20]
                        if rid not in resources:
                            resources[rid] = Resource(rid=rid, name=rname, held_by=pid)
                        edges.append((f"P{pid}", f"R{rid}", EdgeType.HOLDS))
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    pass
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass
    except Exception:
        pass

    return processes, resources, edges


# ---------------------------------------------------------------------------
# Simulation mode  (works without root; great for demos and testing)
# ---------------------------------------------------------------------------

SIMULATION_SCENARIOS = {
    "simple_deadlock": {
        "description": "Classic 2-process deadlock (P1 holds R1, waits R2; P2 holds R2, waits R1)",
        "processes": [
            {"pid": 101, "name": "browser",   "priority": 6},
            {"pid": 102, "name": "database",  "priority": 8},
        ],
        "resources": [
            {"rid": "R1", "name": "File Lock A"},
            {"rid": "R2", "name": "File Lock B"},
        ],
        "edges": [
            (101, "R1", "holds"),
            (102, "R2", "holds"),
            (101, "R2", "waits_for"),
            (102, "R1", "waits_for"),
        ],
    },
    "three_process_deadlock": {
        "description": "3-process circular wait: P1->R1->P2->R2->P3->R3->P1",
        "processes": [
            {"pid": 201, "name": "web_server",  "priority": 7},
            {"pid": 202, "name": "auth_service", "priority": 5},
            {"pid": 203, "name": "db_writer",   "priority": 9},
        ],
        "resources": [
            {"rid": "R1", "name": "Socket Port 8080"},
            {"rid": "R2", "name": "DB Connection"},
            {"rid": "R3", "name": "Config File"},
        ],
        "edges": [
            (201, "R1", "holds"),
            (202, "R2", "holds"),
            (203, "R3", "holds"),
            (201, "R2", "waits_for"),
            (202, "R3", "waits_for"),
            (203, "R1", "waits_for"),
        ],
    },
    "no_deadlock": {
        "description": "Normal operation — no circular wait",
        "processes": [
            {"pid": 301, "name": "editor",    "priority": 4},
            {"pid": 302, "name": "compiler",  "priority": 6},
        ],
        "resources": [
            {"rid": "R1", "name": "Source File"},
            {"rid": "R2", "name": "Output File"},
        ],
        "edges": [
            (301, "R1", "holds"),
            (302, "R2", "holds"),
            (302, "R1", "waits_for"),
        ],
    },
    "near_deadlock": {
        "description": "Near-deadlock: one more acquisition away from a cycle",
        "processes": [
            {"pid": 401, "name": "service_A", "priority": 5},
            {"pid": 402, "name": "service_B", "priority": 7},
            {"pid": 403, "name": "service_C", "priority": 3},
        ],
        "resources": [
            {"rid": "R1", "name": "Mutex Alpha"},
            {"rid": "R2", "name": "Mutex Beta"},
            {"rid": "R3", "name": "Semaphore G"},
        ],
        "edges": [
            (401, "R1", "holds"),
            (402, "R2", "holds"),
            (401, "R2", "waits_for"),
            (403, "R3", "holds"),
        ],
    },
}


def load_scenario(scenario_name: str):
    """Load a named simulation scenario and return (processes, resources, edges)."""
    s = SIMULATION_SCENARIOS.get(scenario_name)
    if not s:
        raise ValueError(f"Unknown scenario: {scenario_name}. "
                         f"Choose from: {list(SIMULATION_SCENARIOS.keys())}")

    processes = {}
    for p in s["processes"]:
        processes[p["pid"]] = Process(
            pid=p["pid"], name=p["name"],
            priority=p.get("priority", 5),
            status=ProcessStatus.RUNNING,
        )

    resources = {}
    for r in s["resources"]:
        resources[r["rid"]] = Resource(rid=r["rid"], name=r["name"])

    edges = []
    for (pid, rid, etype) in s["edges"]:
        etype_enum = EdgeType.HOLDS if etype == "holds" else EdgeType.WAITS_FOR
        edge = (f"P{pid}", f"R{rid}", etype_enum)
        edges.append(edge)

        # Update resource held_by / waited_by
        if etype == "holds":
            resources[rid].held_by = pid
        else:
            resources[rid].waited_by.append(pid)
            processes[pid].status = ProcessStatus.WAITING

    return processes, resources, edges


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_rag(processes: dict, resources: dict, edges: list) -> nx.DiGraph:
    """
    Build the Resource Allocation Graph as a NetworkX DiGraph.

    Node attributes:
      - node_type: "process" | "resource"
      - label: human-readable name
      - data: the underlying Process or Resource object

    Edge attributes:
      - edge_type: "holds" | "waits_for"
    """
    G = nx.DiGraph()

    for pid, proc in processes.items():
        G.add_node(f"P{pid}", node_type=NodeType.PROCESS, label=f"{proc.name}\n(PID {pid})", data=proc)

    for rid, res in resources.items():
        G.add_node(f"R{rid}", node_type=NodeType.RESOURCE, label=f"{res.name}\n[{rid}]", data=res)

    for (src, dst, etype) in edges:
        G.add_edge(src, dst, edge_type=etype)

    return G


def get_wait_for_graph(G: nx.DiGraph) -> nx.DiGraph:
    """
    Derive the pure wait-for graph (process -> process) from the RAG.
    P_i waits for P_j  iff  P_i waits for some resource R that P_j holds.
    """
    WFG = nx.DiGraph()

    for node, data in G.nodes(data=True):
        if data.get("node_type") == NodeType.PROCESS:
            WFG.add_node(node, **data)

    for (u, v, edata) in G.edges(data=True):
        if edata.get("edge_type") == EdgeType.WAITS_FOR:
            # u (process) waits for v (resource)
            # find who holds v
            for (holder, res, he) in G.edges(data=True):
                if res == v and he.get("edge_type") == EdgeType.HOLDS:
                    if u != holder:
                        WFG.add_edge(u, holder, resource=v)

    return WFG


class DataIngestionModule:
    """High-level API for the ingestion module."""

    def __init__(self, mode: str = "simulation", scenario: str = "simple_deadlock"):
        """
        mode: "simulation" | "live"
        scenario: name from SIMULATION_SCENARIOS (used only in simulation mode)
        """
        self.mode = mode
        self.scenario = scenario
        self.processes = {}
        self.resources = {}
        self.edges = []
        self.G = None

    def ingest(self):
        """Fetch data and (re)build the RAG. Returns the DiGraph."""
        if self.mode == "live":
            self.processes, self.resources, self.edges = read_live_processes()
            if not self.processes:
                # Graceful fallback if live read fails
                print("[Ingestion] Live read returned no data; falling back to simulation.")
                self.processes, self.resources, self.edges = load_scenario(self.scenario)
        else:
            self.processes, self.resources, self.edges = load_scenario(self.scenario)

        self.G = build_rag(self.processes, self.resources, self.edges)
        return self.G

    def get_scenario_names(self):
        return list(SIMULATION_SCENARIOS.keys())

    def get_scenario_description(self, name):
        return SIMULATION_SCENARIOS.get(name, {}).get("description", "")
