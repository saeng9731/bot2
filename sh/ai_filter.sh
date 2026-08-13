#!/bin/bash
# ai_filter.sh - Linux용 AI 필터 실행 스크립트 (오라클 클라우드 서버용)
# 사용법: bash ai_filter.sh <db_name> <simul_num>

echo "ai_filter Start"

# 프로젝트 루트 디렉토리
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Python 가상환경 활성화 (필요한 경우 아래 주석 해제)
# source /path/to/venv/bin/activate

# 환경 변수 설정 (필요한 경우 .env 파일 로드)
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

if [ "$#" -ne 2 ]; then
    echo "인자 2개를 입력 해주세요: db_name simul_num"
    echo "예: bash ai_filter.sh JackBot1_imi1 1"
    exit 1
fi

python ai_filter.py $1 $2

echo "ai_filter 작업 완료"