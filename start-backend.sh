#!/usr/bin/env bash
# Start backend API server
set -e
cd "$(dirname "$0")/backend"
pip install -r requirements.txt -q
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
