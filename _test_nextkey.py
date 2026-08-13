import sys, os
sys.path.insert(0, '/home/opc/bot2')
os.chdir('/home/opc/bot2')

import requests
from library.kiwoom_api import KiwoomRestClient, cf

client = KiwoomRestClient()
url = f'{client.base_url}/api/dostk/chart'

headers = {
    'Content-Type': 'application/json;charset=UTF-8',
    'authorization': f'Bearer {client.access_token}',
    'api-id': 'ka10081',
    'cont-yn': 'F',
    'next-key': '',
}
body = {'stk_cd': '005930', 'base_dt': '20260806', 'upd_stkpc_tp': '1'}

r1 = requests.post(url, headers=headers, json=body, timeout=30)
d1 = r1.json()
rows1 = d1.get('stk_dt_pole_chart_qry', [])

print('1차: cont-yn 헤더=', r1.headers.get('cont-yn'))
print('1차: next-key 헤더=', repr(r1.headers.get('next-key')))
print('1차: next-key body=', repr(d1.get('next_key', d1.get('next-key', d1.get('cont', '')))))
print('1차 데이터:', len(rows1), '범위:', rows1[-1]['dt'], '~', rows1[0]['dt'])

nk = r1.headers.get('next-key') or d1.get('next_key') or d1.get('next-key') or ''
print('\n사용할 next-key:', repr(nk))

if nk:
    h2 = dict(headers)
    h2['cont-yn'] = 'T'
    h2['next-key'] = nk
    r2 = requests.post(url, headers=h2, json=body, timeout=30)
    d2 = r2.json()
    rows2 = d2.get('stk_dt_pole_chart_qry', [])
    print('\n2차: 데이터', len(rows2), '범위:', rows2[-1]['dt'], '~', rows2[0]['dt'] if rows2 else '없음')
    print('2차 첫날짜가 1차와 다른가?', (rows2[-1]['dt'] != rows1[-1]['dt']) if rows2 else 'N/A')
else:
    print('\nnext-key가 없음 -> 연속조회 불가 (원인!)')
