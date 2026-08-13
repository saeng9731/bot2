import pymysql

con = pymysql.connect(host='localhost', port=3306, user='bot', password='nastar79', db='daily_craw', charset='utf8mb4')
cur = con.cursor()

# 테이블 목록 확인
cur.execute("select table_name from information_schema.tables where table_schema='daily_craw' order by table_name")
tables = [r[0] for r in cur.fetchall()]
print('로컬 daily_craw 테이블 수:', len(tables))

# 삼성전자 확인
for name in ['삼성전자', 'SK하이닉스', 'NAVER', '카카오']:
    try:
        cur.execute(f'select count(*), min(date), max(date) from `{name}`')
        n, mn, mx = cur.fetchone()
        print(f'{name}: {n}건, {mn} ~ {mx}')
    except Exception as e:
        print(f'{name}: {e}')

# 테이블 중 하나 확인 (첫 번째)
if tables:
    t = tables[0]
    cur.execute(f'select count(*), min(date), max(date) from `{t}`')
    n, mn, mx = cur.fetchone()
    print(f'{t}: {n}건, {mn} ~ {mx}')

con.close()
