# Roadmap Checklist: Phase 4 (Multi-Agent Spatial Sync)

This checklist tracks the technical milestones for the "Scaling VPS Clinical Dashboard" objective.

## 🟢 Module 1: Spatial Engine (Architect)
- `[x]` Debug pipeline crash (85% Feature Mapping).
- `[x]` Implement Area Anchor persistence (Backend API done).
- `[x]` Implement Hybrid Localization (ORB + SIFT fallback for confidence boost).
- `[x]` Spatial Coordinate Calibration utility (`backend/scripts/calibrate_scene.py`).

## 🔵 Module 2: Interaction Orchestrator (Sync)
- `[x]` Create `AgentSession` DB model.
- `[x]` Implement WebSocket broadcaster `/ws/vps/agents`.
- `[x]` Latency benchmarking for sub-100ms pose updates (Verified with test scripts).

## 🔴 Module 3: Platform UX (Dashboard)
- `[x]` Integrate `Framer Motion` for smooth 3D glyph transitions.
- `[x]` Implement "Active Agent" list in the scene sidebar.
- `[x]` Real-time pose projection in the Gaussian Splat viewer.
