import sys
import os
sys.path.insert(0, '/home/opc/bot2')
os.chdir('/home/opc/bot2')

import requests
from library.kiwoom_api import KiwoomRestClient, cf

client = KiwoomRestClient()
url = f'{client.base_url}/api/dostk/chart'

# 첫 조회
headers1 = {
    'Content-Type': 'application/json;charset=UTF-8',
    'authorization': f'Bearer {client.access_token}',
    'cont-yn': 'F',
    'next-key': '',
    'api-id': 'ka10081',
}
body = {'stk_cd': '005930', 'base_dt': '20260806', 'upd_stkpc_tp': '1'}
r1 = requests.post(url, headers=headers1, json=body, timeout=30)
d1 = r1.json()
print('1차 cont-yn 헤더:', r1.headers.get('cont-yn'))
print('1차 next-key 헤더:', r1.headers.get('next-key'))
print('1차 데이터:', len(d1.get('stk_dt_pole_chart_qry', [])))
first_dt1 = d1['stk_dt_pole_chart_qry'][0]['dt']
last_dt1 = d1['stk_dt_pole_chart_qry'][-1]['dt']
print('1차 범위:', last_dt1, '~', first_dt1)

# 연속조회 - cont-yn: 'T' 시도
nk = r1.headers.get('next-key', '')
h2 = dict(headers1)
h2['cont-yn'] = 'T'
h2['next-key'] = nk
r2 = requests.post(url, headers=h2, json=body, timeout=30)
d2 = r2.json()
rows2 = d2.get('stk_dt_pole_chart_qry', [])
print('\n2차(T) cont-yn 헤더:', r2.headers.get('cont-yn'))
print('2차(T) next-key 헤더:', r2.headers.get('next-key'))
print('2차(T) 데이터:', len(rows2))
if rows2:
    print('2차(T) 범위:', rows2[-1]['dt'], '~', rows2[0]['dt'])
    print('2차(T) 첫 날짜가 1차와 다른가?', rows2[-1]['dt'] != last_dt1)
