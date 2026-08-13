import pymysql
import sys
sys.path.insert(0, '/home/opc/bot2')
from library import cf
con = pymysql.connect(host=cf.db_ip, port=int(cf.db_port), user=cf.db_id, password=cf.db_passwd, charset='utf8mb4')
cur = con.cursor()
for db in ['daily_craw', 'min_craw', 'daily_buy_list', 'JackBot11_imi1']:
    cur.execute("select table_name from information_schema.tables where table_schema=%s", (db,))
    tables = [r[0] for r in cur.fetchall()]
    date_tables = [t for t in tables if t.isdigit() and len(t) == 8]
    print(f'{db}: 테이블 {len(tables)}개', end='')
    if date_tables:
        print(f'  (날짜 {len(date_tables)}개, 최신: {max(date_tables)})')
    else:
        print()
con.close()
