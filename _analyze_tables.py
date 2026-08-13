import pymysql
pymysql.install_as_MySQLdb()
from sqlalchemy import create_engine, text
from library import cf

eng = create_engine(f"mysql+pymysql://{cf.db_id}:{cf.db_passwd}@{cf.db_ip}:{cf.db_port}/daily_craw")

# 모든 테이블 목록 (stock_* 제외, 종목 테이블만)
tables = [r[0] for r in eng.execute(text(
    "SELECT table_name FROM information_schema.tables WHERE table_schema='daily_craw' "
    "AND table_name NOT LIKE 'stock\\_%'"))]

print(f"전체 종목 테이블 수: {len(tables)}")

with_data = 0
empty = 0
short_600 = 0   # 600일 이하 (REST로만 수집된 것으로 추정)
long_600 = 0    # 600일 초과 (덤프로 이전된 데이터)
short_list = []
long_list = []

for t in tables:
    try:
        cnt = eng.execute(text(f"SELECT COUNT(DISTINCT date) FROM `{t}`")).fetchone()[0]
        if cnt == 0:
            empty += 1
        elif cnt <= 600:
            short_600 += 1
            short_list.append((t, cnt))
        else:
            long_600 += 1
            long_list.append((t, cnt))
    except Exception:
        empty += 1

print(f"\n=== 결과 ===")
print(f"데이터 없는(빈) 테이블: {empty}개")
print(f"600일 이하 (REST만 수집): {short_600}개")
print(f"600일 초과 (덤프 이전): {long_600}개")

print(f"\n=== 600일 이하 종목 (예시 20개) ===")
for t, c in short_list[:20]:
    print(f"  {t}: {c}일")
if len(short_list) > 20:
    print(f"  ... 외 {len(short_list)-20}개")

print(f"\n=== 600일 초과 종목 (예시 20개) ===")
for t, c in long_list[:20]:
    print(f"  {t}: {c}일")
if len(long_list) > 20:
    print(f"  ... 외 {len(long_list)-20}개")
