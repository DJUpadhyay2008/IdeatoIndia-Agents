#!/bin/bash
# ============================================================
# IdeaToIndia – Local Agent Launcher (no Docker required)
# ============================================================
# Usage:
#   ./run_agents.sh           → starts all agents
#   ./run_agents.sh arch      → starts only the Architecture agent
#   ./run_agents.sh dashboard → starts only the Dashboard
# ============================================================

VENV="./streamlit_agent/.venv/bin/streamlit"
PYTHONPATH_VAL="/home/dutt/IdeaToIndia"

start_agent() {
  local label=$1
  local script=$2
  local port=$3
  echo "▶  Starting $label on http://localhost:$port ..."
  PYTHONPATH="$PYTHONPATH_VAL" "$VENV" run "$script" \
    --server.port "$port" \
    --server.address 0.0.0.0 \
    --server.headless true &
  echo "   PID: $!"
}

case "${1:-all}" in
  vision|1)
    start_agent "Vision & Mission" agents/1_vision_mission/app.py 8502 ;;
  research|2)
    start_agent "Market Research" agents/2_research/app.py 8503 ;;
  requirements|3)
    start_agent "Requirements" agents/3_requirements/app.py 8504 ;;
  planning|4)
    start_agent "Planning" agents/4_planning/app.py 8505 ;;
  arch|architecture|5)
    start_agent "Architecture" agents/5_architecture/app.py 8506 ;;
  dashboard)
    start_agent "Dashboard" agents/dashboard/app.py 8501 ;;
  all)
    start_agent "Dashboard"      agents/dashboard/app.py            8501
    start_agent "Vision Mission" agents/1_vision_mission/app.py     8502
    start_agent "Research"       agents/2_research/app.py           8503
    start_agent "Requirements"   agents/3_requirements/app.py       8504
    start_agent "Planning"       agents/4_planning/app.py           8505
    start_agent "Architecture"   agents/5_architecture/app.py       8506
    ;;
  *)
    echo "Unknown agent: $1"
    echo "Valid options: vision, research, requirements, planning, arch, dashboard, all"
    exit 1 ;;
esac

echo ""
echo "All requested agents started. Use 'kill %1 %2 ...' or Ctrl+C to stop them."
wait
