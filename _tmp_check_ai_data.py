import pymysql
import sys
sys.path.insert(0, '/home/opc/bot2')
from library import cf

con = pymysql.connect(host=cf.db_ip, port=int(cf.db_port), user=cf.db_id, password=cf.db_passwd, db='daily_craw', charset='utf8mb4')
cur = con.cursor()

# 1. 삼성전자 date 컬럼 형식 확인
cur.execute("select date from `삼성전자` limit 3")
print('삼성전자 date 샘플:', [r[0] for r in cur.fetchall()])

# 2. ai_filter와 동일한 쿼리로 건수 확인
cur.execute("select count(*) from `삼성전자` where STR_TO_DATE(date, '%Y%m%d%H%i') <= '20250804'")
print('삼성전자 ~20250804 (ai_filter 쿼리):', cur.fetchone()[0])

# 3. 350건 미만인 종목이 얼마나 되는지 (샘플 100개)
cur.execute("select table_name from information_schema.tables where table_schema='daily_craw' limit 100")
tables = [r[0] for r in cur.fetchall()]
over350 = 0
under350 = 0
for t in tables:
    try:
        cur.execute("select count(*) from `" + t + "` where STR_TO_DATE(date, '%Y%m%d%H%i') <= '20250804'")
        n = cur.fetchone()[0]
        if n >= 350:
            over350 += 1
        else:
            under350 += 1
    except Exception:
        under350 += 1
print('샘플 100개 중 350건 이상:', over350, '/ 350 미만:', under350)

con.close()
