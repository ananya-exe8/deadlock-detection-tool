"""
Module 3: GUI & Visualization
------------------------------
PyQt6-based desktop interface with:
  - Live/simulated RAG graph canvas (matplotlib embedded in Qt)
  - Deadlock detection status panel
  - Resolution strategies sidebar
  - Scenario selector for demo/simulation mode
  - Export to PNG and JSON report
"""

import sys
import json
import time
from datetime import datetime

import networkx as nx
import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QTextEdit, QSplitter,
    QGroupBox, QScrollArea, QFileDialog, QStatusBar, QFrame,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QColor

from models import NodeType, EdgeType, ProcessStatus
from ingestion import DataIngestionModule, SIMULATION_SCENARIOS
from engine import DetectionEngine


# ── colour palette ──────────────────────────────────────────────────────────
COLORS = {
    "process_ok":         "#4CAF50",   # green
    "process_waiting":    "#FF9800",   # orange
    "process_deadlocked": "#F44336",   # red
    "process_at_risk":    "#FF5722",   # deep orange
    "resource":           "#2196F3",   # blue
    "edge_holds":         "#555555",
    "edge_waits":         "#E53935",
    "bg":                 "#FAFAFA",
    "panel_bg":           "#FFFFFF",
}

LEGEND_PATCHES = [
    mpatches.Patch(color=COLORS["process_ok"],         label="Process (running)"),
    mpatches.Patch(color=COLORS["process_waiting"],    label="Process (waiting)"),
    mpatches.Patch(color=COLORS["process_deadlocked"], label="Process (deadlocked)"),
    mpatches.Patch(color=COLORS["resource"],           label="Resource"),
    mpatches.Patch(color=COLORS["edge_holds"],         label="Holds"),
    mpatches.Patch(color=COLORS["edge_waits"],         label="Waits for"),
]


# ── Matplotlib graph canvas ─────────────────────────────────────────────────

class RAGCanvas(FigureCanvas):
    def __init__(self, parent=None):
        self.fig, self.ax = plt.subplots(figsize=(7, 5))
        self.fig.patch.set_facecolor(COLORS["bg"])
        super().__init__(self.fig)
        self.setParent(parent)

    def draw_graph(self, G: nx.DiGraph, at_risk_nodes: list = None):
        self.ax.clear()
        self.ax.set_facecolor(COLORS["bg"])
        self.ax.set_title("Resource Allocation Graph", fontsize=11, pad=10)
        self.ax.axis("off")

        if G is None or len(G.nodes) == 0:
            self.ax.text(0.5, 0.5, "No data to display",
                         ha="center", va="center", transform=self.ax.transAxes,
                         color="gray", fontsize=12)
            self.draw()
            return

        at_risk = set(at_risk_nodes or [])

        # Layout
        try:
            pos = nx.spring_layout(G, seed=42, k=2.5)
        except Exception:
            pos = nx.circular_layout(G)

        # Node colours
        node_colors = []
        node_shapes_proc = [n for n, d in G.nodes(data=True) if d.get("node_type") == NodeType.PROCESS]
        node_shapes_res  = [n for n, d in G.nodes(data=True) if d.get("node_type") == NodeType.RESOURCE]

        def proc_color(n):
            data = G.nodes[n].get("data")
            if data and data.status == ProcessStatus.DEADLOCKED:
                return COLORS["process_deadlocked"]
            if n in at_risk:
                return COLORS["process_at_risk"]
            if data and data.status == ProcessStatus.WAITING:
                return COLORS["process_waiting"]
            return COLORS["process_ok"]

        # Draw process nodes (circles)
        if node_shapes_proc:
            nx.draw_networkx_nodes(
                G, pos,
                nodelist=node_shapes_proc,
                node_color=[proc_color(n) for n in node_shapes_proc],
                node_size=1600, node_shape="o",
                ax=self.ax, alpha=0.92,
            )

        # Draw resource nodes (squares via diamond shape)
        if node_shapes_res:
            nx.draw_networkx_nodes(
                G, pos,
                nodelist=node_shapes_res,
                node_color=COLORS["resource"],
                node_size=1400, node_shape="s",
                ax=self.ax, alpha=0.85,
            )

        # Edges
        holds_edges = [(u, v) for u, v, d in G.edges(data=True)
                       if d.get("edge_type") == EdgeType.HOLDS]
        waits_edges = [(u, v) for u, v, d in G.edges(data=True)
                       if d.get("edge_type") == EdgeType.WAITS_FOR]

        nx.draw_networkx_edges(G, pos, edgelist=holds_edges,
                               edge_color=COLORS["edge_holds"],
                               arrows=True, arrowsize=20,
                               connectionstyle="arc3,rad=0.08",
                               ax=self.ax, width=1.5)

        nx.draw_networkx_edges(G, pos, edgelist=waits_edges,
                               edge_color=COLORS["edge_waits"],
                               arrows=True, arrowsize=20, style="dashed",
                               connectionstyle="arc3,rad=0.08",
                               ax=self.ax, width=2.0)

        # Labels
        labels = {n: G.nodes[n].get("label", n) for n in G.nodes}
        nx.draw_networkx_labels(G, pos, labels=labels,
                                font_size=7, font_color="white",
                                font_weight="bold", ax=self.ax)

        self.ax.legend(handles=LEGEND_PATCHES, loc="lower left",
                       fontsize=7, framealpha=0.8)

        self.fig.tight_layout()
        self.draw()


# ── Worker thread for background polling ────────────────────────────────────

class PollingWorker(QThread):
    data_ready = pyqtSignal(object, object)   # G, report

    def __init__(self, ingestion_module, interval_ms=1500):
        super().__init__()
        self.ingestion = ingestion_module
        self.interval = interval_ms / 1000.0
        self._running = True

    def run(self):
        while self._running:
            G = self.ingestion.ingest()
            engine = DetectionEngine(G)
            report = engine.run()
            near = engine.near_deadlock_nodes()
            self.data_ready.emit(G, (report, near))
            time.sleep(self.interval)

    def stop(self):
        self._running = False


# ── Main window ──────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Automated Deadlock Detection Tool")
        self.resize(1200, 720)

        self.ingestion = DataIngestionModule(mode="simulation", scenario="simple_deadlock")
        self.current_G = None
        self.current_report = None
        self.near_deadlock = []
        self._worker = None

        self._build_ui()
        self._refresh()   # initial draw

    # ── UI construction ──────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(6)

        # ── top toolbar ──
        toolbar = QHBoxLayout()

        toolbar.addWidget(QLabel("Scenario:"))
        self.scenario_combo = QComboBox()
        for name in SIMULATION_SCENARIOS:
            self.scenario_combo.addItem(name)
        self.scenario_combo.currentTextChanged.connect(self._on_scenario_change)
        toolbar.addWidget(self.scenario_combo)

        toolbar.addWidget(QLabel("  Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["simulation", "live"])
        self.mode_combo.currentTextChanged.connect(self._on_mode_change)
        toolbar.addWidget(self.mode_combo)

        toolbar.addStretch()

        self.btn_refresh = QPushButton("⟳  Refresh")
        self.btn_refresh.clicked.connect(self._refresh)
        toolbar.addWidget(self.btn_refresh)

        self.btn_auto = QPushButton("▶  Auto-Poll (1.5s)")
        self.btn_auto.setCheckable(True)
        self.btn_auto.toggled.connect(self._toggle_auto_poll)
        toolbar.addWidget(self.btn_auto)

        self.btn_export = QPushButton("⬇  Export")
        self.btn_export.clicked.connect(self._export)
        toolbar.addWidget(self.btn_export)

        root_layout.addLayout(toolbar)

        # ── status banner ──
        self.status_banner = QLabel("Status: Idle")
        self.status_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_banner.setFixedHeight(32)
        self.status_banner.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self._set_banner("idle")
        root_layout.addWidget(self.status_banner)

        # ── splitter: graph | sidebar ──
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Graph
        self.canvas = RAGCanvas()
        splitter.addWidget(self.canvas)

        # Sidebar
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(4, 0, 4, 0)

        # Scenario description
        self.desc_label = QLabel()
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("color: #555; font-size: 11px;")
        sidebar_layout.addWidget(self.desc_label)

        # Detection summary
        summary_box = QGroupBox("Detection Summary")
        summary_layout = QVBoxLayout(summary_box)
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setMaximumHeight(120)
        self.summary_text.setFont(QFont("Courier New", 9))
        summary_layout.addWidget(self.summary_text)
        sidebar_layout.addWidget(summary_box)

        # Resolution strategies
        res_box = QGroupBox("Resolution Strategies")
        res_layout = QVBoxLayout(res_box)
        self.resolution_text = QTextEdit()
        self.resolution_text.setReadOnly(True)
        self.resolution_text.setFont(QFont("Arial", 9))
        res_layout.addWidget(self.resolution_text)
        sidebar_layout.addWidget(res_box)

        splitter.addWidget(sidebar)
        splitter.setSizes([750, 430])
        root_layout.addWidget(splitter)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    # ── event handlers ───────────────────────────────────────────────────

    def _on_scenario_change(self, name):
        self.ingestion.scenario = name
        desc = SIMULATION_SCENARIOS.get(name, {}).get("description", "")
        self.desc_label.setText(f"Scenario: {desc}")
        self._refresh()

    def _on_mode_change(self, mode):
        self.ingestion.mode = mode
        self._refresh()

    def _refresh(self):
        G = self.ingestion.ingest()
        engine = DetectionEngine(G)
        report = engine.run()
        near = engine.near_deadlock_nodes()
        self._update_ui(G, (report, near))

    def _toggle_auto_poll(self, checked):
        if checked:
            self.btn_auto.setText("⏹  Stop Auto-Poll")
            self._worker = PollingWorker(self.ingestion, interval_ms=1500)
            self._worker.data_ready.connect(self._update_ui)
            self._worker.start()
        else:
            self.btn_auto.setText("▶  Auto-Poll (1.5s)")
            if self._worker:
                self._worker.stop()
                self._worker.wait()
                self._worker = None

    def _update_ui(self, G, result_tuple):
        report, near = result_tuple
        self.current_G = G
        self.current_report = report
        self.near_deadlock = near

        self.canvas.draw_graph(G, at_risk_nodes=near)
        self._update_summary(G, report, near)
        self._update_resolution(report)
        self._update_banner(report, near)

    def _update_banner(self, report, near):
        if report:
            self._set_banner("deadlock")
        elif near:
            self._set_banner("at_risk")
        else:
            self._set_banner("safe")

    def _set_banner(self, state: str):
        styles = {
            "idle":     ("Status: Idle — Load a scenario or click Refresh",
                         "background:#E0E0E0; color:#555;"),
            "safe":     ("✔  No deadlock detected — system is healthy",
                         "background:#C8E6C9; color:#1B5E20;"),
            "at_risk":  ("⚠  Near-deadlock detected — processes approaching circular wait",
                         "background:#FFE0B2; color:#E65100;"),
            "deadlock": ("✖  DEADLOCK DETECTED — immediate action required",
                         "background:#FFCDD2; color:#B71C1C;"),
        }
        text, style = styles.get(state, styles["idle"])
        self.status_banner.setText(text)
        self.status_banner.setStyleSheet(style + " padding: 4px; border-radius: 4px;")

    def _update_summary(self, G, report, near):
        lines = []
        lines.append(f"Nodes: {G.number_of_nodes()}  |  Edges: {G.number_of_edges()}")

        proc_count = sum(1 for _, d in G.nodes(data=True) if d.get("node_type") == NodeType.PROCESS)
        res_count  = sum(1 for _, d in G.nodes(data=True) if d.get("node_type") == NodeType.RESOURCE)
        lines.append(f"Processes: {proc_count}  |  Resources: {res_count}")

        if report:
            lines.append(f"\nDEADLOCK  [{report.timestamp}]")
            lines.append(f"Cycle: {' → '.join(report.cycle)}")
            lines.append(f"Processes: {', '.join(p.name for p in report.involved_processes)}")
        elif near:
            lines.append(f"\nAt-risk processes: {', '.join(near)}")
        else:
            lines.append("\nNo deadlock detected.")

        self.summary_text.setPlainText("\n".join(lines))

    def _update_resolution(self, report):
        if not report:
            self.resolution_text.setHtml(
                "<p style='color:gray;'>No deadlock detected. No strategies needed.</p>"
            )
            return

        html = []
        for s in report.resolution_strategies:
            color = ["#C62828", "#E65100", "#1565C0", "#2E7D32"][s["rank"] - 1]
            html.append(
                f"<p><b style='color:{color};'>[{s['rank']}] {s['action']}</b> "
                f"— <i>{s['target_label'].replace(chr(10), ' ')}</i><br/>"
                f"{s['description']}<br/>"
                f"<span style='color:#666;'>Impact: {s['impact']}</span></p><hr/>"
            )
        self.resolution_text.setHtml("".join(html))

    # ── export ────────────────────────────────────────────────────────────

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export", f"deadlock_report_{datetime.now():%Y%m%d_%H%M%S}",
            "JSON Report (*.json);;PNG Image (*.png)"
        )
        if not path:
            return

        if path.endswith(".png"):
            self.canvas.fig.savefig(path, dpi=150, bbox_inches="tight")
            self.status_bar.showMessage(f"Graph exported to {path}")

        elif path.endswith(".json"):
            data = {
                "exported_at": datetime.now().isoformat(),
                "scenario": self.scenario_combo.currentText(),
                "deadlock_detected": self.current_report is not None,
                "near_deadlock_nodes": self.near_deadlock,
            }
            if self.current_report:
                r = self.current_report
                data["report"] = {
                    "timestamp": r.timestamp,
                    "cycle": r.cycle,
                    "involved_processes": [
                        {"pid": p.pid, "name": p.name, "priority": p.priority}
                        for p in r.involved_processes
                    ],
                    "involved_resources": [
                        {"rid": res.rid, "name": res.name}
                        for res in r.involved_resources
                    ],
                    "resolution_strategies": r.resolution_strategies,
                }
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
            self.status_bar.showMessage(f"Report exported to {path}")

    def closeEvent(self, event):
        if self._worker:
            self._worker.stop()
            self._worker.wait()
        event.accept()


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
