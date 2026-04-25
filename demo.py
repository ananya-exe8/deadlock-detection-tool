"""
CLI Demo Runner
---------------
Demonstrates the Deadlock Detection Tool without requiring a GUI.
Run this to show the tool working in a terminal — great for live demos.

Usage:
    python demo.py                         # runs all scenarios
    python demo.py simple_deadlock         # single scenario
    python demo.py three_process_deadlock
"""
import sys
import time
from ingestion import DataIngestionModule, SIMULATION_SCENARIOS
from engine import DetectionEngine


BANNER = """
╔══════════════════════════════════════════════════════╗
║     Automated Deadlock Detection Tool  v1.0          ║
║     CLI Demo — all scenarios                         ║
╚══════════════════════════════════════════════════════╝
"""


def run_scenario(name: str):
    print(f"\n{'─'*60}")
    desc = SIMULATION_SCENARIOS[name].get("description", "")
    print(f"  SCENARIO: {name}")
    print(f"  {desc}")
    print(f"{'─'*60}")

    ingestion = DataIngestionModule(mode="simulation", scenario=name)
    G = ingestion.ingest()

    print(f"  Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    engine = DetectionEngine(G)
    report = engine.run()
    near   = engine.near_deadlock_nodes()

    if report:
        engine.print_report()
    elif near:
        print(f"\n  ⚠  NEAR-DEADLOCK: Processes at risk: {near}")
        print("  These processes hold resources AND are waiting — one step from deadlock.\n")
    else:
        print("\n  ✔  No deadlock detected. System state is healthy.\n")


def main():
    print(BANNER)

    if len(sys.argv) > 1:
        scenarios = [sys.argv[1]]
    else:
        scenarios = list(SIMULATION_SCENARIOS.keys())

    for scenario in scenarios:
        if scenario not in SIMULATION_SCENARIOS:
            print(f"Unknown scenario: {scenario}")
            print(f"Available: {list(SIMULATION_SCENARIOS.keys())}")
            sys.exit(1)
        run_scenario(scenario)
        time.sleep(0.3)   # small pause for readability

    print("\nDemo complete. Launch gui.py for the interactive interface.\n")


if __name__ == "__main__":
    main()
