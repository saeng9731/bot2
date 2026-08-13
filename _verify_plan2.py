import pymysql
pymysql.install_as_MySQLdb()
from sqlalchemy import create_engine, text
from library import cf

eng = create_engine(f"mysql+pymysql://{cf.db_id}:{cf.db_passwd}@{cf.db_ip}:{cf.db_port}/daily_craw")

print("=== 1) 복원된 daily_craw 테이블 수 & 대표 종목 날짜 ===")
cnt = eng.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='daily_craw'")).fetchone()[0]
print(f"  테이블 수: {cnt}")

for t in ['삼성전자', 'NAVER', '현대자동차', 'LG전자', '카카오']:
    try:
        mn = eng.execute(text(f"SELECT MIN(date) FROM `{t}`")).fetchone()[0]
        mx = eng.execute(text(f"SELECT MAX(date) FROM `{t}`")).fetchone()[0]
        dc = eng.execute(text(f"SELECT COUNT(DISTINCT date) FROM `{t}`")).fetchone()[0]
        print(f"  {t}: {dc}일 ({mn} ~ {mx})")
    except Exception as e:
        print(f"  {t}: 테이블 없음 ({type(e).__name__})")

print("\n=== 2) 덤프 파일에 SK하이닉스가 있나? ===")
import subprocess
r = subprocess.run(['grep', '-c', 'INSERT INTO `SK하이닉스`', '/home/opc/bot2_daily_craw_dump.sql'], capture_output=True, text=True)
print(f"  SK하이닉스 INSERT 줄: {r.stdout.strip()}")

print("\n=== 3) REST API 600일 확인 (기준일자=20260809) ===")
import sys, os, requests
sys.path.insert(0, '/home/opc/bot2')
from library.kiwoom_api import KiwoomRestClient
client = KiwoomRestClient()
url = f'{client.base_url}/api/dostk/chart'
headers = {
    'Content-Type': 'application/json;charset=UTF-8',
    'authorization': f'Bearer {client.access_token}',
    'api-id': 'ka10081', 'cont-yn': 'F', 'next-key': '',
}
body = {'stk_cd': '005930', 'base_dt': '20260809', 'upd_stkpc_tp': '1'}
resp = requests.post(url, headers=headers, json=body, timeout=30)
d = resp.json()
rows = d.get('stk_dt_pole_chart_qry', [])
if rows:
    print(f"  API 반환: {len(rows)}건")
    print(f"  범위: {rows[-1]['dt']} ~ {rows[0]['dt']}")
    print(f"  cont-yn 헤더: {resp.headers.get('cont-yn')}")
else:
    print(f"  API 응답 없음: {str(d)[:300]}")
