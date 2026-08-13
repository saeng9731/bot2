import pymysql
import sys
sys.path.insert(0, '/home/opc/bot2')
from library import cf

con = pymysql.connect(host=cf.db_ip, port=int(cf.db_port), user=cf.db_id, password=cf.db_passwd, db='daily_craw', charset='utf8mb4')
cur = con.cursor()

cur.execute("select table_name from information_schema.tables where table_schema='daily_craw'")
tables = [r[0] for r in cur.fetchall()]
print('전체 테이블 수:', len(tables))

# 몇 개 종목의 데이터 건수/날짜 범위 조사
import random
random.seed(42)
sample = random.sample(tables, min(20, len(tables)))

counts = []
for t in sample:
    try:
        cur.execute('select count(*), min(date), max(date) from `' + t + '`')
        n, mn, mx = cur.fetchone()
        counts.append(n)
        print(f'{t}: {n}건, {mn} ~ {mx}')
    except Exception as e:
        print(f'{t}: ERR {e}')

# 건수 분포 요약
if counts:
    counts.sort()
    print('\n샘플 건수 분포:')
    print('  최소:', counts[0])
    print('  최대:', counts[-1])
    print('  중앙값:', counts[len(counts)//2])

# 특정 대형주 확인
for name in ['삼성전자', 'SK하이닉스', 'NAVER', '카카오']:
    try:
        cur.execute('select count(*), min(date), max(date) from `' + name + '`')
        n, mn, mx = cur.fetchone()
        print(f'{name}: {n}건, {mn} ~ {mx}')
    except Exception as e:
        print(f'{name}: 테이블 없음/에러 {e}')

con.close()
