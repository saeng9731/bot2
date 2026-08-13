import pymysql
import sys
sys.path.insert(0, '/home/opc/bot2')
from library import cf

con = pymysql.connect(host=cf.db_ip, port=int(cf.db_port), user=cf.db_id, password=cf.db_passwd, db=cf.imi1_db_name, charset='utf8mb4')
cur = con.cursor()

# jango_data 테이블 존재 확인
cur.execute("select table_name from information_schema.tables where table_schema=%s and table_name='jango_data'", (cf.imi1_db_name,))
print('jango_data 존재:', cur.fetchone()[0] if cur.rowcount else 0)

# 컬럼 확인
cur.execute("show columns from jango_data")
print('\n컬럼:')
for r in cur.fetchall():
    print('  ', r[0], r[1])

# 데이터 확인
cur.execute("select count(*) from jango_data")
print('\n전체 행 수:', cur.fetchone()[0])

cur.execute("select date, total_asset, today_profit, total_profit from jango_data order by date desc limit 10")
print('\n최근 10일:')
for r in cur.fetchall():
    print('  ', r)

con.close()
