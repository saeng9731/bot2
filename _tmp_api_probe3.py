import sys
import os
sys.path.insert(0, '/home/opc/bot2')
os.chdir('/home/opc/bot2')

import requests
from library.kiwoom_api import KiwoomRestClient, cf

client = KiwoomRestClient()
url = f'{client.base_url}/api/dostk/chart'
headers = {
    'Content-Type': 'application/json;charset=UTF-8',
    'authorization': f'Bearer {client.access_token}',
    'cont-yn': 'F',
    'next-key': '',
    'api-id': 'ka10081',
}
body = {
    'stk_cd': '005930',
    'base_dt': '20260806',
    'upd_stkpc_tp': '1',   # 문자열!
}

resp = requests.post(url, headers=headers, json=body, timeout=30)
data = resp.json()
print('HTTP', resp.status_code)
print('return_msg:', data.get('return_msg'))
print('return_code:', data.get('return_code'))
print('최상위 키:', list(data.keys()))

# 연속조회 관련 키 확인
for k in ['cont', 'next', 'next_key', 'next-key', 'tr_cnt', 'total_cnt', 'count']:
    if k in data:
        print(f'  {k}:', data[k])

# 응답 헤더에서 연속조회 확인
print('응답 헤더 cont-yn:', resp.headers.get('cont-yn'))
print('응답 헤더 next-key:', resp.headers.get('next-key'))

# 데이터 배열
for key in ['stk_dt_pole_chart_qry', 'stk_dt_pole_qry', 'output', 'output1']:
    if key in data:
        out = data[key]
        if isinstance(out, list):
            print(f'[{key}] {len(out)}건')
            if out:
                print('  첫:', out[0])
                print('  마지막:', out[-1])
