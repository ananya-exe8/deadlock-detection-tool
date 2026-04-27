# 🔍 Deadlock Detection Tool - React Web Application

## Automated Deadlock Detection Tool for Operating Systems

A modern, redesigned web application for detecting and visualizing deadlocks in operating system processes using industry-standard algorithms — rebuilt with a clean TypeScript + Tailwind CSS interface.

[![React](https://img.shields.io/badge/React-18.3-blue)](https://reactjs.org/)
[![Vite](https://img.shields.io/badge/Vite-5.4-646CFF)](https://vitejs.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178C6)](https://www.typescriptlang.org/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4-38BDF8)](https://tailwindcss.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Modern redesigned UI for the Deadlock Detective tool. Built with React 18, TypeScript, Vite 5, and Tailwind CSS. Implements Matrix-Based and Wait-For Graph deadlock detection algorithms with an interactive, responsive interface.

---

## 👥 Project Team

**Academic Project - Lovely Professional University**  
**Course:** CSE 316 - Operating Systems 

**Team Members:**
Ananya N : 12406258
Roshan : 12404131

## 📖 Overview

**Deadlock Detection Tool** is a redesigned web-based educational tool that helps students and developers understand **deadlock detection** in operating systems. It retains the full algorithm logic from the original project while delivering a completely refreshed, modern UI built with Tailwind CSS and TypeScript.

**Perfect for:**
- 🎓 Students learning Operating Systems
- 👨‍🏫 Educators teaching concurrency and synchronization
- 💻 Developers studying resource management
- 📚 Anyone interested in how computers handle process deadlocks

---

## 🎯 Problem Statement

> **"Develop a tool that automatically detects potential deadlocks in system processes. The tool should analyze process dependencies and resource allocation to identify circular wait conditions and suggest resolution strategies."**

### Solution Implemented

This web application:

1. ✅ **Analyzes** process dependencies and resource allocations
2. ✅ **Detects** deadlocks using two proven algorithms
3. ✅ **Visualizes** system state with interactive graphs
4. ✅ **Explains** detection process step-by-step
5. ✅ **Suggests** multiple recovery strategies

---

## ✨ Key Features

### 🔍 **Dual Detection Algorithms**

- **Matrix-Based Detection** - Uses Work/Finish vectors for multi-instance resources (O(n²×m))
- **Wait-For Graph (WFG)** - Uses cycle detection for single-instance resources (O(n²))
- Automatic algorithm selection based on system configuration

### 🎨 **Redesigned Modern UI**

- Built with **Tailwind CSS** for a clean, utility-first design
- Fully responsive layout (desktop, tablet, mobile)
- Dark-themed professional interface
- Smooth hover effects and transitions throughout

### 📝 **Educational Traces**

- Complete step-by-step algorithm execution
- Shows Work vector updates (Matrix algorithm)
- Displays cycle detection process (WFG algorithm)
- Detailed explanations for learning

### 🔧 **Smart Recovery Strategies**

- **Process Termination**: Minimal sets to break deadlock
- **Resource Preemption**: Suggests which resources to reclaim
- **What-If Simulation**: Shows system state after recovery
- Multiple ranked options

### 💾 **5 Pre-loaded Sample Datasets**

1. **Circular Deadlock** - Classic 3-process circular wait
2. **Safe State** - Multi-instance resources, no deadlock
3. **Multi-Instance Deadlock** - Deadlock with multiple resource instances
4. **Partial Deadlock** - Some processes safe, others deadlocked
5. **Complex Safe State** - 5 processes with safe execution sequence

### 🌐 **Modern Web Interface**

- ✅ No installation required - runs in any modern browser
- ✅ Responsive design (desktop, tablet, mobile)
- ✅ TypeScript for type-safe development
- ✅ Editable allocation and request matrices
- ✅ Lucide React icons throughout the interface
- ✅ Built and bundled with Vite 5 for fast performance

---

## 🚀 Quick Start

### Prerequisites

- **Node.js** 18+ and npm
- Modern web browser (Chrome, Firefox, Edge, Safari)

### Installation

```bash
# Clone the repository

# Install dependencies
npm install

# Start development server
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

### First Usage

1. **Load a Sample**: Click any sample dataset button
2. **Analyze**: Click "🔍 Analyze for Deadlock"
3. **View Results**: See detection results and traces
4. **Explore Visualization**: Switch to the Visualization tab
5. **Try Recovery**: Review suggested recovery strategies

---

## 📂 Project Structure

```
OS Deadlock Detection Tool/
└── project/
    ├── src/
    │   ├── algorithms/          # Core detection algorithms
    │   │   ├── matrix.ts        # Matrix-based detection (multi-instance)
    │   │   ├── wfg.ts           # Wait-For Graph detection (single-instance)
    │   │   └── recovery.ts      # Recovery strategy generation
    │   │
    │   ├── components/          # React UI components
    │   │   ├── Header.tsx       # Application header
    │   │   ├── InputTab.tsx     # Data entry interface
    │   │   ├── VisualizationTab.tsx  # Graph visualization
    │   │   └── ResultsTab.tsx   # Results and traces display
    │   │
    │   ├── types/               # TypeScript type definitions
    │   │   └── models.ts        # SystemState, Process, Resource types
    │   │
    │   ├── utils/               # Utilities
    │   │   └── samples.ts       # Sample datasets & JSON I/O
    │   │
    │   ├── App.tsx              # Main application component
    │   └── main.tsx             # Entry point
    │
    ├── public/                  # Static assets
    ├── index.html               # HTML entry point
    ├── vite.config.ts           # Vite configuration
    ├── tailwind.config.js       # Tailwind CSS configuration
    ├── tsconfig.json            # TypeScript configuration
    ├── postcss.config.js        # PostCSS configuration
    ├── package.json             # Dependencies
    └── README.md                # This file
```

---

## 🎓 Algorithms Explained

### Matrix-Based Detection Algorithm

**Best for:** Resources with **multiple instances** (e.g., 3 printers, 5 memory blocks)

**How it works:**
1. Initialize `Work = Available` and `Finish[i] = false` for all processes
2. Find a process `i` where `Finish[i] == false` and `Request[i] ≤ Work`
3. Mark `Finish[i] = true` and update `Work = Work + Allocation[i]`
4. Repeat until no more processes can finish
5. Any `Finish[i] == false` → Process `i` is deadlocked

**Time Complexity:** O(n² × m) where n = processes, m = resource types

### Wait-For Graph (WFG) Algorithm

**Best for:** Resources with **single instances** (e.g., 1 printer, 1 scanner)

**How it works:**
1. Build directed graph: `Pi → Pj` if Pi waits for a resource held by Pj
2. Detect cycles using Depth-First Search (DFS)
3. Any cycle found → Deadlock exists
4. Processes in cycles are deadlocked

**Time Complexity:** O(n²) where n = processes

---

## 🎮 Usage Guide

### Input Tab

**Load Sample Dataset:**
- Click any sample button to auto-populate data
- Perfect for learning and experimentation

**Edit System State:**
- **Resource Types Table**: Edit total instances per resource
- **Allocation Matrix**: Current resource holdings (who has what)
- **Request Matrix**: Resource requests (who wants what)

**Run Detection:**
- Click "🔍 Analyze for Deadlock" button
- Algorithm runs automatically
- Results appear in Results tab

### Visualization Tab

**Graph Elements:**
- **Circles** = Processes (P0, P1, ...)
- **Rectangles** = Resources (R0, R1, ...)
- **Colors**:
  - Blue = Safe process
  - Red = Deadlocked process
  - Purple = Resource
- **Edges**:
  - Green solid arrow = Allocation (resource → process)
  - Yellow dashed arrow = Request (process → resource)

### Results Tab

**Status Banner:**
- ✅ Green = System is safe
- 🚨 Red = Deadlock detected

**Detection Trace:**
- Step-by-step algorithm execution
- Shows all calculations and decisions
- Educational for understanding algorithms

**Recovery Strategies:**
- **Process Termination**: Which processes to terminate
- **Resource Preemption**: Which resources to reclaim
- **Explanations**: Why each strategy works

---

## 📊 Example Scenarios

### Scenario 1: Circular Deadlock

```
P0: Has R0, Wants R1
P1: Has R1, Wants R2
P2: Has R2, Wants R0

Result: DEADLOCK (circular wait: P0 → P1 → P2 → P0)
```

### Scenario 2: Safe State

```
P0: Has [1,0], Wants [0,1], Can finish!
P1: Has [0,1], Wants [1,0], Waits...
P2: Has [0,0], Wants [0,0], Can finish!

Result: SAFE (execution order: P0 → P2 → P1)
```

---

## 🧪 Testing

### Manual Testing

```bash
# Start dev server
npm run dev

# Test each sample dataset
# Test matrix editing
# Test visualization rendering
# Test recovery strategies
```

### Type Checking

```bash
# Run TypeScript type checker
npm run typecheck
```

### Build for Production

```bash
# Create optimized build
npm run build

# Preview production build
npm run preview
```

---

## 🚀 Deployment

### Deploy to Vercel

```bash
npm install -g vercel
vercel deploy
```

### Deploy to Netlify

```bash
npm run build
# Upload dist/ folder to Netlify
```

### Deploy to GitHub Pages

```bash
npm run build
# Push dist/ folder to gh-pages branch
```

---

## 💻 Technologies Used

| Technology | Purpose | Version |
|------------|---------|---------|
| **React** | UI framework | 18.3.1 |
| **Vite** | Build tool & dev server | 5.4.2 |
| **TypeScript** | Type-safe JavaScript | 5.5.3 |
| **Tailwind CSS** | Utility-first CSS framework | 3.4.1 |
| **Lucide React** | Icon library | 0.344.0 |
| **PostCSS** | CSS processing | 8.4.35 |
| **ESLint** | Code linting | 9.9.1 |
| **Supabase JS** | Backend client (optional) | 2.57.4 |


## 🎓 Academic Project Details

**Institution:** Lovely Professional University  
**School:** Computer Science and Engineering   
**Course Code:** CSE 316  
**Course Title:** Operating Systems  

### Problem Statement

> **"Automated Deadlock Detection Tool: Develop a tool that automatically detects potential deadlocks in system processes. The tool should analyze process dependencies and resource allocation to identify circular wait conditions and suggest resolution strategies."**

### Project Objectives

1. ✅ Implement automated deadlock detection algorithms
2. ✅ Analyze process dependencies and resource allocation
3. ✅ Identify circular wait conditions
4. ✅ Provide visual representation of system state
5. ✅ Suggest resolution strategies for detected deadlocks
