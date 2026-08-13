import sys
import os
sys.path.insert(0, '/home/opc/bot2')
os.chdir('/home/opc/bot2')

from library.kiwoom_api import open_api

api = open_api()
api.py_gubun = 'collector'

df = api.get_total_data('005930', '삼성전자', api.today)
print('총 건수:', len(df))
print('고유 날짜 수:', df['date'].nunique())
print('날짜 범위:', df['date'].min(), '~', df['date'].max())

# 중복 확인
dups = df[df.duplicated(subset='date', keep=False)]
print('중복 행 수:', len(dups))
if len(dups) > 0:
    print('중복 날짜 예시:', dups['date'].head(5).tolist())
