import sys
import os
sys.path.insert(0, '/home/opc/bot2')
os.chdir('/home/opc/bot2')

from library.kiwoom_api import open_api

# 테스트: 삼성전자 일봉 데이터 전체를 API에서 조회
api = open_api()
api.py_gubun = 'collector'

try:
    df = api.get_total_data('005930', '삼성전자', api.today)
    print('반환 데이터 건수:', len(df) if df is not None else 0)
    if df is not None and len(df) > 0:
        print('날짜 범위:', df['date'].min(), '~', df['date'].max())
except Exception as e:
    print('오류:', e)
