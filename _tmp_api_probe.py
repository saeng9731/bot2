import sys
import os
sys.path.insert(0, '/home/opc/bot2')
os.chdir('/home/opc/bot2')

from library.kiwoom_api import KiwoomRestClient

client = KiwoomRestClient()

# ka10081 직접 호출 - 응답 구조 확인
params = {'stk_cd': '005930', 'base_dt': '20260806', 'upd_stkpc_tp': 1}
resp = client.request('ka10081', params)

print('응답 최상위 키:', list(resp.keys()))
# 연속조회 관련 필드 확인
for k in ['cont', 'next', 'cont_key', 'tr_cnt', 'total_cnt']:
    print(f'{k}:', resp.get(k))

# 데이터 배열 확인
data = resp.get('stk_dt_pole_chart_qry', resp.get('output', []))
print('이번 응답 데이터 건수:', len(data) if isinstance(data, list) else 'list 아님')
if isinstance(data, list) and data:
    print('첫 데이터:', data[0])
    print('마지막 데이터:', data[-1])
