#!/usr/bin/env bash
# launch.sh – helper to set up a virtual environment and run the Streamlit app

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip and install dependencies (skip if already satisfied)
pip install --upgrade pip
pip install -r requirements.txt

# Run Streamlit UI
streamlit run app.py
