#!/bin/bash
# ============================================================
#  min_craw.sh - 분봉(min_craw) 전용 수집 스크립트 (서버용)
# ============================================================
#  메인 콜렉터(collector.sh)와 분리해서 분봉만 빠르게 수집한다.
#  실행: bash sh/min_craw.sh
#
#  crontab 등록 예시 (메인 콜렉터와 같은 15:35~23:59 창 안에서)
#  - 주의! 서버 시간대가 UTC 이므로 한국시간 15:45 = UTC 06:45
#    40 6 * * 1-5 cd /home/opc/bot2 && source /home/opc/new_autobot_env_py311/bin/activate && bash sh/min_craw.sh >> /home/opc/bot2/log/min_craw_cron.log 2>&1
#  - 메인 콜렉터(UTC 06:30 = 한국 15:30)가 종목코드/stock_info를
#    갱신한 뒤(약 10분)에 시작하면 check_min_crawler 초기화와 안 겹침
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# 환경 변수 로드
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

# ---------- conda 가상환경 자동 활성화 (crontab에서도 동작) ----------
CONDA_BASE=""
if [ -f "/home/opc/new_autobot_env_py311/bin/activate" ]; then
    CONDA_BASE="/home/opc/new_autobot_env_py311"
elif [ -f "/home/opc/anaconda3/bin/activate" ]; then
    CONDA_BASE="/home/opc/anaconda3"
elif [ -f "/home/opc/miniconda3/bin/activate" ]; then
    CONDA_BASE="/home/opc/miniconda3"
elif [ -f "/opt/conda/bin/activate" ]; then
    CONDA_BASE="/opt/conda"
fi

if [ -n "$CONDA_BASE" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] conda 환경 활성화: $CONDA_BASE"
    source "$CONDA_BASE/bin/activate"
fi

# ---------- 이중 실행 방지 (crontab/수동 실행이 겹치면 스킵) ----------
if pgrep -f "min_craw.py" > /dev/null 2>&1; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] min_craw.py 이미 실행 중입니다. 이번 실행은 스킵합니다."
    exit 0
fi

echo "======================================================"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 분봉(min_craw) 전용 콜렉터 시작"
echo "======================================================"

python min_craw.py
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 분봉(min_craw) 수집 완료"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 분봉(min_craw) 수집 실패 (코드: ${EXIT_CODE})"
fi

exit $EXIT_CODE
