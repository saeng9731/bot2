#!/bin/bash
# ============================================================
#  콜렉터 무한 재시작 스크립트 (Windows 스케줄러 대체)
#  - conda 가상환경 자동 활성화 포함 (crontab에서도 동작)
#  - 콜렉터가 실패/중단되면 자동으로 다시 실행 (무한)
#  - 성공하면 종료
#  - 실행: bash sh/collector_auto.sh
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# 환경 변수 로드
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

# ---------- conda 가상환경 자동 활성화 (crontab에서도 동작) ----------
# conda 환경 경로 시도 순서
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

RETRY_COUNT=0
# 같은 실패로 무한 반복되는 것을 방지하기 위한 최대 재시도 횟수
MAX_RETRY=3

while true; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "======================================================"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 콜렉터 실행 시도 ${RETRY_COUNT}회차"
    echo "======================================================"

    # 핵심 콜렉터 실행 (exit code를 정확히 받기 위해 python 직접 실행)
    python collector_v3.py
    EXIT_CODE=$?

    # 성공적으로 완료되면 종료 (exit 0 = 정상 완료)
    if [ $EXIT_CODE -eq 0 ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 콜렉터가 성공적으로 완료되었습니다."
        break
    fi

    # 최대 재시도 횟수 초과 시 중단 (같은 에러로 밤새 도는 것 방지)
    if [ $RETRY_COUNT -ge $MAX_RETRY ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 콜렉터가 ${MAX_RETRY}회 연속 실패했습니다. log/jackbot.log 를 확인하세요."
        exit 1
    fi

    # 실패 시 재시도
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 콜렉터 실패 (코드: ${EXIT_CODE}). 10초 후 재시작... (${RETRY_COUNT}/${MAX_RETRY})"
    sleep 10
done