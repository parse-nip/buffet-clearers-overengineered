#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
export PYTHONIOENCODING=utf-8
python -m pip install -r requirements.txt
python run_graphs.py
