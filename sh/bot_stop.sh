#!/bin/bash
echo bot_stop Start
# Windows bot_stop.bat 대체: collector / trader 등 강제 종료 (크론 23:59에 실행)
pkill -f "collector_auto.sh" 2>/dev/null || true
pkill -f "collector_v3.py" 2>/dev/null || true
pkill -f "min_craw.py" 2>/dev/null || true
pkill -f "kind_crawling.py" 2>/dev/null || true
pkill -f "trader.sh" 2>/dev/null || true
pkill -f "trader.py" 2>/dev/null || true
pkill -f "simulator_v2.py" 2>/dev/null || true
pkill -f "ai_filter.py" 2>/dev/null || true
echo done
