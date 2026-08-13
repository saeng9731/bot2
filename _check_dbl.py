import pymysql
pymysql.install_as_MySQLdb()
from sqlalchemy import create_engine, text
from library import cf

eng = create_engine(f"mysql+pymysql://{cf.db_id}:{cf.db_passwd}@{cf.db_ip}:{cf.db_port}/daily_buy_list")

# 1) daily_buy_list의 테이블 수
tables = eng.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='daily_buy_list'")).fetchall()
print("=== daily_buy_list 테이블 수:", len(tables))

# 2) 날짜 테이블 vs 종목 테이블 구분
date_tables = [t[0] for t in tables if t[0].isdigit() and len(t[0]) == 8]
other_tables = [t[0] for t in tables if not (t[0].isdigit() and len(t[0]) == 8)]
print(f"날짜 테이블(20250804 형식): {len(date_tables)}개")
print(f"기타 테이블: {len(other_tables)}개")
print(f"기타 테이블 목록: {other_tables[:10]}")

# 3) 날짜 테이블 범위
if date_tables:
    date_tables.sort()
    print(f"\n날짜 테이블 범위: {date_tables[0]} ~ {date_tables[-1]}")
    # 각 날짜 테이블의 행 수 확인 (첫/마지막)
    for dt in [date_tables[0], date_tables[-1]]:
        try:
            cnt = eng.execute(text(f"SELECT COUNT(*) FROM `{dt}`")).fetchone()[0]
            print(f"  {dt}: {cnt}행")
        except Exception as e:
            print(f"  {dt}: 오류 {e}")
