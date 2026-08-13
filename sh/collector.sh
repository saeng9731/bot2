#!/bin/bash
# collector.sh - Linux용 콜렉터 실행 스크립트 (오라클 클라우드 서버용)
# 키움증권 REST API 기반이므로 Linux에서도 콜렉터 실행 가능!
# 1) REST API로 일봉/분봉 데이터 수집 (collector_v3.py)
# 2) KIND 크롤링으로 종목 리스트 수집 (kind_crawling.py)

echo "collector Start"

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

# 키움 REST API로 일봉/분봉 데이터 수집 (Linux에서도 동작!)
# 주의: collector_v3.py 내부에서 self.kind.craw() 로 KIND 크롤링이 자동 실행됨.
#       별도로 kind_crawling.py 를 실행하면 중복 실행되므로 제거함.
python collector_v3.py

echo "collector 작업 완료"
