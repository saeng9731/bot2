#!/bin/bash
# ============================================================
#  kind_crawling.py 자동 재시작 스크립트 (ARM 서버 안정화용)
#  - 크롬이 죽어 크롤링 프로세스가 중단되면 자동으로 다시 실행
#  - DB에는 get_last_date_from 기준으로 이어서 진행되므로 중복 없음
#  - 실행: bash sh/kind_crawl_retry.sh
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# conda 환경 활성화
ENV_PATH="/home/opc/new_autobot_env_py311"
if [ -f "$ENV_PATH/bin/activate" ]; then
    source "$ENV_PATH/bin/activate"
fi

RETRY_COUNT=0
MAX_RETRY=5

while true; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "======================================================"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] kind_crawling 실행 시도 ${RETRY_COUNT}회차"
    echo "======================================================"

    python -u kind_crawling.py
    EXIT_CODE=$?

    # 성공(exit 0)이면 종료
    if [ $EXIT_CODE -eq 0 ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] kind_crawling 성공적으로 완료되었습니다."
        break
    fi

    # 최대 재시도 횟수 초과 시 중단
    if [ $RETRY_COUNT -ge $MAX_RETRY ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] kind_crawling이 ${MAX_RETRY}회 연속 실패했습니다. 로그를 확인하세요."
        exit 1
    fi

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] kind_crawling 실패 (코드: ${EXIT_CODE}). 15초 후 재시작... (${RETRY_COUNT}/${MAX_RETRY})"
    sleep 15
done
