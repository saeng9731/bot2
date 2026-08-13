import pymysql
import sys
sys.path.insert(0, '/home/opc/bot2')
from library import cf
con = pymysql.connect(host=cf.db_ip, port=int(cf.db_port), user=cf.db_id, password=cf.db_passwd, db=cf.imi1_db_name, charset='utf8mb4')
cur = con.cursor()

# 1. realtime_daily_buy_list에 이상한 코드가 있는지
try:
    cur.execute("select code, code_name from realtime_daily_buy_list where code not regexp '^[0-9]{6}$' limit 30")
    rows = cur.fetchall()
    print('realtime_daily_buy_list 비정상 코드 수:', len(rows))
    for r in rows:
        print('  ', r)
except Exception as e:
    print('realtime_daily_buy_list 조회 실패:', e)

# 2. daily_buy_list 날짜 테이블에 이상한 코드가 있는지 (최신 날짜)
try:
    cur.execute("select code from daily_buy_list.`20260804` where code not regexp '^[0-9]{6}$' limit 20")
    rows = cur.fetchall()
    print('daily_buy_list.20260804 비정상 코드 수:', len(rows))
    for r in rows:
        print('  ', r)
except Exception as e:
    print('daily_buy_list 조회 실패:', e)

con.close()
