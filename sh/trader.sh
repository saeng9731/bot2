#!/bin/bash
# trader.sh - Linux용 트레이더 실행 스크립트 (오라클 클라우드 서버용)
# bat/trader.bat (Windows) 에 대응하는 Linux 스크립트
# 트레이더 프로세스가 종료되면 자동으로 재시작합니다.

echo "trader Start"

# 프로젝트 루트 디렉토리
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# ---------- conda 가상환경 자동 활성화 (crontab/direct 실행 모두 동작) ----------
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

# 환경 변수 설정 (필요한 경우 .env 파일 로드)
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

# 트레이더 무한 재시작 루프 (bat/trader.bat 의 :repeat 루프와 동일)
while true; do
    echo "trader.py 실행 중..."
    python trader.py
    echo "trader.py 종료됨. 5초 후 재시작..."
    sleep 5
done