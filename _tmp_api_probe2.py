import sys
import os
sys.path.insert(0, '/home/opc/bot2')
os.chdir('/home/opc/bot2')

from library.kiwoom_api import KiwoomRestClient

client = KiwoomRestClient()

# 다양한 파라미터 조합 시도
attempts = [
    {'stk_cd': '005930', 'base_dt': '20260806', 'upd_stkpc_tp': 1},
    {'stk_cd': '005930', 'upd_stkpc_tp': 1},
    {'stk_cd': '005930'},
]
for params in attempts:
    resp = client.request('ka10081', params)
    print('params:', params)
    print('  return_code:', resp.get('return_code'), '| return_msg:', resp.get('return_msg'))
    keys = [k for k in resp.keys() if k not in ('return_code', 'return_msg')]
    print('  데이터 키:', keys)
    for k in keys:
        v = resp.get(k)
        if isinstance(v, list):
            print(f'  {k}: {len(v)}건')
            if v:
                print('    첫:', v[0])
    print()
