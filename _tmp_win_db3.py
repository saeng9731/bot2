import pymysql

con = pymysql.connect(host='localhost', port=3306, user='bot', password='nastar79', charset='utf8mb4')
cur = con.cursor()

# daily_craw 전체 크기 확인
cur.execute("""
    SELECT 
      ROUND(SUM(data_length + index_length) / 1024 / 1024, 1) AS size_mb,
      COUNT(DISTINCT table_name) AS table_count
    FROM information_schema.tables
    WHERE table_schema = 'daily_craw'
""")
r = cur.fetchone()
print(f'daily_craw 크기: {r[0]} MB, 테이블: {r[1]}개')

# 테이블별 크기 상위 5개
cur.execute("""
    SELECT table_name, ROUND((data_length + index_length) / 1024 / 1024, 1) AS size_mb
    FROM information_schema.tables
    WHERE table_schema = 'daily_craw'
    ORDER BY (data_length + index_length) DESC
    LIMIT 5
""")
print('\n큰 테이블 TOP5:')
for r in cur.fetchall():
    print(f'  {r[0]}: {r[1]} MB')

# daily_buy_list 크기도 확인
cur.execute("""
    SELECT 
      ROUND(SUM(data_length + index_length) / 1024 / 1024, 1) AS size_mb,
      COUNT(DISTINCT table_name) AS table_count
    FROM information_schema.tables
    WHERE table_schema = 'daily_buy_list'
""")
r = cur.fetchone()
print(f'\ndaily_buy_list 크기: {r[0]} MB, 테이블: {r[1]}개')

con.close()
