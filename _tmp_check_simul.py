import pymysql
import sys
sys.path.insert(0, '/home/opc/bot2')
from library import cf
con = pymysql.connect(host=cf.db_ip, port=int(cf.db_port), user=cf.db_id, password=cf.db_passwd, charset='utf8mb4')
cur = con.cursor()

# 1. daily_craw의 gs글로벌 테이블 확인
cur.execute("select table_name from information_schema.tables where table_schema='daily_craw' and table_name='gs글로벌'")
print('gs글로벌 테이블 존재:', cur.fetchone()[0] if cur.rowcount else 0)

# 2. gs글로벌의 날짜 범위
try:
    cur.execute("select min(date), max(date), count(distinct date) from daily_craw.`gs글로벌`")
    r = cur.fetchone()
    print(f'gs글로벌 날짜: {r[0]} ~ {r[1]}, 거래일 {r[2]}개')
except Exception as e:
    print('gs글로벌 조회 실패:', e)

# 3. daily_buy_list 날짜 테이블 범위
cur.execute("select table_name from information_schema.tables where table_schema='daily_buy_list' and table_name regexp '[0-9]{8}' order by table_name")
rows = [r[0] for r in cur.fetchall()]
print(f'daily_buy_list 날짜 테이블: {len(rows)}개, 최소 {rows[0] if rows else None}, 최대 {rows[-1] if rows else None}')

# 4. daily_craw에서 최신 일봉 데이터 확인 (삼성전자)
try:
    cur.execute("select max(date) from daily_craw.`005930`")
    print('삼성전자 daily_craw 최신:', cur.fetchone()[0])
except Exception as e:
    print('삼성전자 조회 실패:', e)

con.close()
