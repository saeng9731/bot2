import pymysql
import sys
sys.path.insert(0, '/home/opc/bot2')
from library import cf
con = pymysql.connect(host=cf.db_ip, port=int(cf.db_port), user=cf.db_id, password=cf.db_passwd, db='daily_buy_list', charset='utf8mb4')
cur = con.cursor()
cur.execute("select table_name from information_schema.tables where table_schema='daily_buy_list' order by table_name desc limit 30")
rows = cur.fetchall()
print('daily_buy_list 테이블 수:', len(rows))
for r in rows:
    print(r[0])
con.close()
