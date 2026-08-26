#!/bin/bash
cd "$(dirname "$0")/backend"
source venv/bin/activate
echo "🚀 Starting backend at http://localhost:8000"
python main.py
