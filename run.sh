#!/usr/bin/env bash
cd "$(dirname "$0")"
echo "========================================================"
echo "  Rajasthan Royals Scouting Engine - SupeRR Selector"
echo "========================================================"
echo ""
echo "Starting Django server on http://127.0.0.1:8000 ..."
python manage.py runserver 127.0.0.1:8000
