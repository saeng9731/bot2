import pymysql
import sys
sys.path.insert(0, '/home/opc/bot2')
from library import cf

con = pymysql.connect(host=cf.db_ip, port=int(cf.db_port), user=cf.db_id, password=cf.db_passwd, db='simulator11', charset='utf8mb4')
cur = con.cursor()

cur.execute("select table_name from information_schema.tables where table_schema='simulator11'")
print('simulator11 테이블:', [r[0] for r in cur.fetchall()])

if 'jango_data' in [r[0] for r in cur.fetchall()]:
    pass
cur.execute("select table_name from information_schema.tables where table_schema='simulator11'")
tables = [r[0] for r in cur.fetchall()]
if 'jango_data' in tables:
    cur.execute("select count(*) from jango_data")
    print('jango_data 행 수:', cur.fetchone()[0])
    cur.execute("select date, total_asset, today_profit, total_profit, sum_valuation_profit from jango_data order by date desc limit 15")
    print('최근 15일:')
    for r in cur.fetchall():
        print('  ', r)
else:
    print('jango_data 없음')

con.close()
