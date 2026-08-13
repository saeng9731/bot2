import pymysql
import sys
import re
sys.path.insert(0, '/home/opc/bot2')
from library import cf

# 시뮬레이션 로그에서 분석 대상 종목들 추출
with open('/tmp/simul_11_v2.log', 'r', encoding='utf-8', errors='ignore') as f:
    log = f.read()

analyzed = re.findall(r'(.+?) 종목 분석 중\.\.\.\.', log)
print('AI 분석 대상 종목 수:', len(analyzed))
print('분석 종목 예시:', analyzed[:10])

con = pymysql.connect(host=cf.db_ip, port=int(cf.db_port), user=cf.db_id, password=cf.db_passwd, db='daily_craw', charset='utf8mb4')
cur = con.cursor()

exist = 0
not_exist = 0
no_data = 0
for name in analyzed:
    cur.execute("select table_name from information_schema.tables where table_schema='daily_craw' and table_name=%s", (name,))
    if cur.rowcount == 0:
        not_exist += 1
    else:
        cur.execute("select count(*) from `" + name + "`")
        n = cur.fetchone()[0]
        if n >= 350:
            exist += 1
        else:
            no_data += 1

print(f'\ndaily_craw에 존재+350건 이상: {exist}')
print(f'daily_craw에 테이블 없음: {not_exist}')
print(f'daily_craw에 있지만 350건 미만: {no_data}')

con.close()
