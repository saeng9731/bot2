import os, sys
os.chdir('/home/opc/bot2')
from library.kiwoom_api import open_api

api = open_api()
df = api.get_total_data('005930', '삼성전자', '20260808')
print('총 행 수 :', len(df))
print('고유 날짜 수 :', df['date'].nunique())
print('중복 날짜 수 :', len(df) - df['date'].nunique())
if len(df) > df['date'].nunique():
    print('>>> 연속조회 버그 있음! 같은 날짜가 반복 수신됨')
else:
    print('>>> 연속조회 정상 (중복 없음)')
