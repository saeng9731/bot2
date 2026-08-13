import pymysql
import sys
sys.path.insert(0, '/home/opc/bot2')
from library import cf
con = pymysql.connect(host=cf.db_ip, port=int(cf.db_port), user=cf.db_id, password=cf.db_passwd, db=cf.imi1_db_name, charset='utf8mb4')
cur = con.cursor()
cur.execute("select count(*) from information_schema.tables where table_schema=%s and table_name=%s", (cf.imi1_db_name, 'realtime_daily_buy_list'))
exists = cur.fetchone()[0]
print('realtime_daily_buy_list exists:', exists)
if exists == 1:
    cur.execute('select count(*) from realtime_daily_buy_list')
    print('rows:', cur.fetchone()[0])
con.close()
