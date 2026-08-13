import pymysql
import sys
sys.path.insert(0, '/home/opc/bot2')
from library import cf
con = pymysql.connect(host=cf.db_ip, port=int(cf.db_port), user=cf.db_id, password=cf.db_passwd, charset='utf8mb4')
cur = con.cursor()

# 최신 날짜 테이블에서 비정상 코드 전체 목록 + code_name 확인
cur.execute("select code, code_name, close from daily_buy_list.`20260804` where code not regexp '^[0-9]{6}$'")
rows = cur.fetchall()
print('20260804 비정상 코드 전체:', len(rows))
for r in rows[:30]:
    print('  ', r)

# 예전 날짜 테이블(예: 20250804)에도 비정상 코드가 있는지
cur.execute("select count(*) from daily_buy_list.`20250804` where code not regexp '^[0-9]{6}$'")
print('20250804 비정상:', cur.fetchone()[0])
cur.execute("select count(*) from daily_buy_list.`20260101` where code not regexp '^[0-9]{6}$'")
print('20260101 비정상:', cur.fetchone()[0])

# 비정상 코드가 시작되는 날짜 찾기
cur.execute("select table_name from information_schema.tables where table_schema='daily_buy_list' and table_name regexp '[0-9]{8}' order by table_name")
date_tables = [r[0] for r in cur.fetchall()]
first_abnormal = None
for t in date_tables:
    cur.execute(f"select count(*) from daily_buy_list.`{t}` where code not regexp '^[0-9]{{6}}$'")
    if cur.fetchone()[0] > 0:
        first_abnormal = t
        break
print('비정상 코드 첫 등장 날짜:', first_abnormal)

con.close()
