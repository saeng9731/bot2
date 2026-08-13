import sys
import os
sys.path.insert(0, '/home/opc/bot2')
os.chdir('/home/opc/bot2')

from library.kiwoom_api import open_api

# 삼성전자 테이블 삭제 후 전체 데이터 조회 테스트
api = open_api()
api.py_gubun = 'collector'

# 기존 테이블 삭제 (안전: 코드에서 is_craw_table_exist가 False가 되도록)
try:
    api.engine_daily_craw.execute('DROP TABLE IF EXISTS daily_craw.`삼성전자`')
    print('삼성전자 테이블 삭제 완료 (재수집 테스트)')
except Exception as e:
    print('테이블 삭제 오류:', e)

try:
    df = api.get_total_data('005930', '삼성전자', api.today)
    print('반환 데이터 건수:', len(df) if df is not None else 0)
    if df is not None and len(df) > 0:
        print('날짜 범위:', df['date'].min(), '~', df['date'].max())
except Exception as e:
    print('오류:', e)
