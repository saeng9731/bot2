#!/bin/bash
# simul_run.sh - Linux용 시뮬레이터 실행 스크립트 (오라클 클라우드 서버용)
# 사용법: bash sh/simul_run.sh 1 4 n
#   인자1: 시작 시뮬레이터 번호
#   인자2: 끝 시뮬레이터 번호
#   인자3: y (초기화) 또는 n (이어서)
# 백그라운드 예: nohup bash sh/simul_run.sh 11 11 n >> log/simul_run.log 2>&1 &

echo "simul_run Start"

# 프로젝트 루트 디렉토리
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# 환경 변수 설정 (필요한 경우 .env 파일 로드)
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

# ---------- conda 가상환경 자동 활성화 (crontab/백그라운드 실행 모두 동작) ----------
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

# 로그 디렉토리 보장
mkdir -p log

if [ "$#" -ne 3 ]; then
    echo "인자 3개를 입력 해주세요: 시작번호 끝번호 y/n"
    echo "예: bash simul_run.sh 1 4 n"
    exit 1
fi

START=$1
END=$2
RESET_OPTION=$3

if [ "$RESET_OPTION" == "y" ]; then
    SIMUL_RESET="reset"
elif [ "$RESET_OPTION" == "n" ]; then
    SIMUL_RESET="continue"
else
    echo "y or n (소문자) 만 입력 가능 합니다."
    exit 1
fi

for i in $(seq $START $END); do
    echo "run: $i"
    python simulator_v2.py $i $SIMUL_RESET &
done

wait
echo "simul_run 작업 완료"