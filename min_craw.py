# ============================================================
#  min_craw.py - 분봉(min_craw) 전용 수집 스크립트
# ============================================================
#  일봉(daily_craw)과 분리해서 분봉만 빠르게 수집한다.
#  - 메인 콜렉터(collector_v3.py)는 일봉 수집이 18시간 걸려서
#    분봉 단계(파이프라인 맨 마지막)에 도달하지 못하는 문제가 있다.
#  - 이 스크립트는 분봉만 골라서 약 1~2시간 안에 전체 종목을 수집한다.
#
#  실행 방법 (Windows):
#      python min_craw.py
#  실행 방법 (서버/Linux):
#      bash sh/min_craw.sh
#
#  동작:
#    1) stock_item_all 에서 check_min_crawler == 0 인 종목만 순회
#       - 이미 수집된 종목(check != 0)은 건너뛰므로 몇 번을 돌려도 안전
#       - 중간에 실패한 종목은 다음 실행에서 자동 재시도
#    2) 각 종목의 1분봉(ka10080) 데이터를 수집해
#       min_craw.{종목명} 테이블을 생성/갱신
#    3) 전부 완료되면 setting_data.min_crawler = 오늘 날짜 로 갱신
#       - 이후 메인 콜렉터가 분봉 단계를 건너뜀
#    4) rate limit(초당 1회) 대응 + 429 재시도 + 크래시 방지 포함
#       (library/kiwoom_api.py get_total_data_min,
#        library/collector_api.py db_to_min_craw 에 이미 반영됨)
# ============================================================
from library.collector_api import collector_api

if __name__ == "__main__":
    print("분봉(min_craw) 전용 콜렉터를 시작합니다.")
    ca = collector_api()
    ca.min_crawler_check()
    print("분봉(min_craw) 수집을 완료했습니다.")
