import pymysql
import sys
sys.path.insert(0, '/home/opc/bot2')
from library import cf

con = pymysql.connect(host=cf.db_ip, port=int(cf.db_port), user=cf.db_id, password=cf.db_passwd, charset='utf8mb4')
cur = con.cursor()

# simulator DB 목록 확인
cur.execute("select schema_name from information_schema.schemata where schema_name like 'simulator%' order by schema_name")
dbs = [r[0] for r in cur.fetchall()]
print('simulator DB 목록:', dbs)

# simulator11 DB의 jango_data 확인
if 'simulator11' in dbs:
    cur.execute("select table_name from information_schema.tables where table_schema='simulator11'")
    tables = [r[0] for r in cur.fetchall()]
    print('simulator11 테이블:', tables)
    if 'jango_data' in tables:
        cur.execute("select count(*) from simulator11.jango_data")
        print('jango_data 행 수:', cur.fetchone()[0])
        cur.execute("select date, total_asset, today_profit, total_profit, sum_valuation_profit from simulator11.jango_data order by date desc limit 10")
        print('최근 10일:')
        for r in cur.fetchall():
            print('  ', r)

con.close()
