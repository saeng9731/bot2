import pymysql
import sys
sys.path.insert(0, '/home/opc/bot2')
from library import cf
con = pymysql.connect(host=cf.db_ip, port=int(cf.db_port), user=cf.db_id, password=cf.db_passwd, charset='utf8mb4')
cur = con.cursor()

# gs글로벌 테이블 존재 여부
cur.execute("select table_name from information_schema.tables where table_schema='daily_craw' and table_name='gs글로벌'")
print('gs글로벌 존재:', cur.rowcount)

# 테이블 하나 골라서 날짜 범위 확인 (예: 삼성전자)
cur.execute("select table_name from information_schema.tables where table_schema='daily_craw' and table_name like '%삼성%'")
sam = [r[0] for r in cur.fetchall()]
print('삼성 관련 테이블:', sam)

if sam:
    t = sam[0]
    cur.execute(f'select min(date), max(date), count(*) from daily_craw.`{t}`')
    r = cur.fetchone()
    print(f'{t}: 날짜 {r[0]} ~ {r[1]}, {r[2]}건')

# 몇 개 테이블의 최신 날짜 확인
cur.execute("select table_name from information_schema.tables where table_schema='daily_craw' order by table_name limit 10")
tables = [r[0] for r in cur.fetchall()]
print('\n첫 10개 테이블 최신 날짜:')
for t in tables:
    try:
        cur.execute(f'select max(date) from daily_craw.`{t}`')
        print(f'  {t}: {cur.fetchone()[0]}')
    except Exception as e:
        print(f'  {t}: ERR {e}')

con.close()
