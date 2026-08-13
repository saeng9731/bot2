import pymysql
pymysql.install_as_MySQLdb()
from sqlalchemy import create_engine, text
from library import cf

eng = create_engine(f"mysql+pymysql://{cf.db_id}:{cf.db_passwd}@{cf.db_ip}:{cf.db_port}/daily_craw")

print("=== 1) 복원된 daily_craw의 각 종목 마지막 날짜 ===")
for t in ['삼성전자', 'SK하이닉스', 'NAVER', '현대자동차']:
    mn = eng.execute(text(f"SELECT MIN(date) FROM `{t}`")).fetchone()[0]
    mx = eng.execute(text(f"SELECT MAX(date) FROM `{t}`")).fetchone()[0]
    cnt = eng.execute(text(f"SELECT COUNT(DISTINCT date) FROM `{t}`")).fetchone()[0]
    print(f"  {t}: {cnt}일 ({mn} ~ {mx})")

print("\n=== 2) REST API가 반환하는 범위 (기준일자=오늘) ===")
import sys, os
sys.path.insert(0, '/home/opc/bot2')
from library.kiwoom_api import KiwoomRestClient
client = KiwoomRestClient()
url = f'{client.base_url}/api/dostk/chart'
import requests
headers = {
    'Content-Type': 'application/json;charset=UTF-8',
    'authorization': f'Bearer {client.access_token}',
    'api-id': 'ka10081', 'cont-yn': 'F', 'next-key': '',
}
body = {'stk_cd': '005930', 'base_dt': '20260809', 'upd_stkpc_tp': '1'}
r = requests.post(url, headers=headers, json=body, timeout=30)
d = r.json()
rows = d.get('stk_dt_pole_chart_qry', [])
if rows:
    print(f"  API 반환: {len(rows)}건, 범위: {rows[-1]['dt']} ~ {rows[0]['dt']}")
    print(f"  cont-yn: {r.headers.get('cont-yn')} (N이면 600건이 전부)")
else:
    print(f"  API 응답 없음: {str(d)[:200]}")

print("\n=== 3) 결론 계산 ===")
print("  복원된 DB 마지막 날짜 이후 + REST가 새로 주는 날짜만 추가되면 OK")
