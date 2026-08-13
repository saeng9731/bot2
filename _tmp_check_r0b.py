import pymysql
import sys
sys.path.insert(0, '/home/opc/bot2')
from library import cf
con = pymysql.connect(host=cf.db_ip, port=int(cf.db_port), user=cf.db_id, password=cf.db_passwd, charset='utf8mb4')
cur = con.cursor()

# daily_buy_list의 최신 날짜 테이블에서 비정상 코드 전체 개수
try:
    cur.execute("select code, count(*) from daily_buy_list.`20260804` where code not regexp '^[0-9]{6}$' group by code order by count(*) desc limit 40")
    rows = cur.fetchall()
    print('20260804 비정상 코드 유형:', len(rows), '종류')
    total = 0
    for r in rows:
        total += r[1]
        print('  ', r)
    print('비정상 코드 전체 건수:', total)
except Exception as e:
    print('조회 실패:', e)

# 전체 날짜 테이블 수와 비정상 포함 여부
cur.execute("select table_name from information_schema.tables where table_schema='daily_buy_list' and table_name regexp '[0-9]{8}' order by table_name")
date_tables = [r[0] for r in cur.fetchall()]
print('날짜 테이블 수:', len(date_tables))

# 가장 최근 몇 개 테이블의 비정상 코드 여부
for t in date_tables[-5:]:
    cur.execute(f"select count(*) from daily_buy_list.`{t}` where code not regexp '^[0-9]{{6}}$'")
    print(f'{t}: 비정상 {cur.fetchone()[0]}건')

con.close()
