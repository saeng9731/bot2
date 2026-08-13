import sys
import os
sys.path.insert(0, '/home/opc/bot2')
os.chdir('/home/opc/bot2')

import requests
from library.kiwoom_api import KiwoomRestClient, cf

client = KiwoomRestClient()
url = f'{client.base_url}/api/dostk/chart'

base_headers = {
    'Content-Type': 'application/json;charset=UTF-8',
    'authorization': f'Bearer {client.access_token}',
    'api-id': 'ka10081',
}
body = {'stk_cd': '005930', 'base_dt': '20260806', 'upd_stkpc_tp': '1'}

# 첫 조회
h1 = dict(base_headers)
h1['cont-yn'] = 'F'
h1['next-key'] = ''
r1 = requests.post(url, headers=h1, json=body, timeout=30)
d1 = r1.json()
nk = r1.headers.get('next-key', '')
print('1차: cont-yn 헤더=', r1.headers.get('cont-yn'), 'next-key=', nk)
print('1차 데이터:', len(d1.get('stk_dt_pole_chart_qry', [])), '범위:', d1['stk_dt_pole_chart_qry'][-1]['dt'], '~', d1['stk_dt_pole_chart_qry'][0]['dt'])

# 방법 A: 헤더 cont-yn=Y, next-key 사용
hA = dict(base_headers)
hA['cont-yn'] = 'Y'
hA['next-key'] = nk
rA = requests.post(url, headers=hA, json=body, timeout=30)
dA = rA.json()
rowsA = dA.get('stk_dt_pole_chart_qry', [])
print('\n[방법A] 헤더 cont-yn=Y: 데이터', len(rowsA), '범위:', (rowsA[-1]['dt'] + '~' + rowsA[0]['dt']) if rowsA else '없음')

# 방법 B: body에 cont 넣기
bodyB = dict(body)
bodyB['cont'] = nk
hB = dict(base_headers)
hB['cont-yn'] = 'Y'
hB['next-key'] = nk
rB = requests.post(url, headers=hB, json=bodyB, timeout=30)
dB = rB.json()
rowsB = dB.get('stk_dt_pole_chart_qry', [])
print('[방법B] body cont + 헤더: 데이터', len(rowsB), '범위:', (rowsB[-1]['dt'] + '~' + rowsB[0]['dt']) if rowsB else '없음')

# 방법 C: cont-yn='T', next-key 헤더 (이미 했지만 재확인)
hC = dict(base_headers)
hC['cont-yn'] = 'T'
hC['next-key'] = nk
rC = requests.post(url, headers=hC, json=body, timeout=30)
dC = rC.json()
rowsC = dC.get('stk_dt_pole_chart_qry', [])
print('[방법C] 헤더 cont-yn=T: 데이터', len(rowsC), '범위:', (rowsC[-1]['dt'] + '~' + rowsC[0]['dt']) if rowsC else '없음')
