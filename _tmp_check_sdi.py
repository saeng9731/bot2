import pymysql
import sys
sys.path.insert(0, '/home/opc/bot2')
from library import cf

con = pymysql.connect(host=cf.db_ip, port=int(cf.db_port), user=cf.db_id, password=cf.db_passwd, charset='utf8mb4')
cur = con.cursor()

# 1. daily_craw에 삼성SDI 테이블 존재?
cur.execute("select table_name from information_schema.tables where table_schema='daily_craw' and table_name='삼성SDI'")
print('삼성SDI 테이블 존재:', cur.rowcount)

# 2. 삼성SDI 전체 데이터 수
cur.execute("select count(*), min(date), max(date) from daily_craw.`삼성SDI`")
print('삼성SDI 전체:', cur.fetchone())

# 3. ai_filter 쿼리 방식으로 조회 (until=20260107 가정)
cur.execute("select count(*) from daily_craw.`삼성SDI` where STR_TO_DATE(date, '%Y%m%d%H%i') <= '20260107'")
print('삼성SDI ~20260107:', cur.fetchone()[0])

# 4. date 컬럼 타입/형식 확인
cur.execute("show columns from daily_craw.`삼성SDI`")
for r in cur.fetchall():
    if r[0] in ('date', 'close', 'volume', 'open', 'high', 'low'):
        print('컬럼:', r[0], r[1])
cur.execute("select date from daily_craw.`삼성SDI` limit 3")
print('date 샘플:', [r[0] for r in cur.fetchall()])

con.close()
