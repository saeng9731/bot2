import pymysql
import io

conn = pymysql.connect(host='127.0.0.1', user='bot', password='nastar79', db='daily_craw', charset='utf8mb4')
cur = conn.cursor()

stocks = ['SK하이닉스', 'NAVER', 'LG전자']

# 테이블 구조 확인용 (첫 테이블 기준)
cur.execute("SHOW CREATE TABLE `SK하이닉스`")
create_sql = cur.fetchone()[1]
print("=== 테이블 구조 (SK하이닉스) ===")
print(create_sql[:500])

out = io.StringIO()

for s in stocks:
    # 테이블 존재 확인
    cur.execute(f"SHOW CREATE TABLE `{s}`")
    row = cur.fetchone()
    if not row:
        print(f"\n{s}: 테이블 없음, 스킵")
        continue
    out.write(f"\n--\n-- Table structure for `{s}`\n--\n")
    out.write(row[1])
    out.write(";\n\n")

    # 데이터 추출
    cur.execute(f"SELECT * FROM `{s}`")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    print(f"{s}: {len(rows)}행")

    out.write(f"--\n-- Data for `{s}`\n--\n")
    for r in rows:
        vals = []
        for v in r:
            if v is None:
                vals.append("NULL")
            elif isinstance(v, (int, float)):
                vals.append(str(v))
            else:
                vals.append("'" + str(v).replace("\\", "\\\\").replace("'", "''") + "'")
        out.write(f"INSERT INTO `{s}` ({','.join('`'+c+'`' for c in cols)}) VALUES ({','.join(vals)});\n")
    out.write("\n")

with open(r'c:\Users\UserK\Desktop\bot2\missing_stocks.sql', 'w', encoding='utf-8') as f:
    f.write("SET NAMES utf8mb4;\n")
    f.write(out.getvalue())

print("\n=== 완료! 파일 크기 ===")
import os
out_path = r'c:\Users\UserK\Desktop\bot2\missing_stocks.sql'
print(os.path.getsize(out_path), "바이트")
conn.close()
