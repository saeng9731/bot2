import pymysql
import sys
sys.path.insert(0, '/home/opc/bot2')
from library import cf
con = pymysql.connect(host=cf.db_ip, port=int(cf.db_port), user=cf.db_id, password=cf.db_passwd, charset='utf8mb4')
cur = con.cursor()

# daily_craw 테이블 목록 (일부)
cur.execute("select table_name from information_schema.tables where table_schema='daily_craw' order by table_name limit 30")
rows = [r[0] for r in cur.fetchall()]
print('daily_craw 첫 30개 테이블:')
for r in rows:
    print(' ', r)

# 테이블명 유형 분류
cur.execute("select table_name from information_schema.tables where table_schema='daily_craw'")
all_tables = [r[0] for r in cur.fetchall()]
import re
code_tables = [t for t in all_tables if re.fullmatch(r'\d{6}', t)]
name_tables = [t for t in all_tables if not re.fullmatch(r'\d{6}', t)]
print(f'\n총 {len(all_tables)}개 / 코드테이블 {len(code_tables)}개 / 기타 {len(name_tables)}개')
print('기타 테이블 예시:', name_tables[:15])

# 가장 최근 데이터를 가진 테이블 찾기 (일부)
con.close()
