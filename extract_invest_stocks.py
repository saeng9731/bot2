# -*- coding: utf-8 -*-
"""
extract_invest_stocks.py - KIND 투자주의/경고/위험 종목 추출 (DB 기반)

bot2 DB(daily_buy_list)의 stock_invest_caution/warning/danger 테이블에서
종목 리스트를 추출해 Excel(xlsx)로 저장.

사용법:
    python extract_invest_stocks.py [출력파일명.xlsx]
"""
import sys, os
import pymysql
pymysql.install_as_MySQLdb()
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
from library import cf

# 테이블별 설정: (테이블명, 분류명, SELECT 할 추가 컬럼)
TABLES = [
    ("stock_invest_caution", "투자주의", "type"),
    ("stock_invest_warning", "투자경고", ""),
    ("stock_invest_danger",  "투자위험", ""),
]

def extract(conn, table, label, extra_col):
    cur = conn.cursor()
    if extra_col:
        sql = f"SELECT code, code_name, `{extra_col}` AS reason, post_date, fix_date, NULL AS cleared_date FROM `{table}`"
    else:
        # danger는 cleared_date 보유, warning은 없음 → 컬럼 존재 확인
        cur.execute(f"SHOW COLUMNS FROM `{table}`")
        cols = [c[0] for c in cur.fetchall()]
        if "cleared_date" in cols:
            sql = f"SELECT code, code_name, NULL AS reason, post_date, fix_date, cleared_date FROM `{table}`"
        else:
            sql = f"SELECT code, code_name, NULL AS reason, post_date, fix_date, NULL AS cleared_date FROM `{table}`"
    df = pd.read_sql(sql, conn)
    df.insert(0, "분류", label)
    return df

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "kind_invest_stocks.xlsx"
    conn = pymysql.connect(host=cf.db_ip, port=int(cf.db_port), user=cf.db_id,
                           password=cf.db_passwd, database="daily_buy_list",
                           charset="utf8mb4")
    dfs = [extract(conn, t, label, extra) for t, label, extra in TABLES]
    combined = pd.concat(dfs, ignore_index=True)
    combined = combined[["분류", "code", "code_name", "reason", "post_date", "fix_date", "cleared_date"]]
    combined["code"] = combined["code"].astype(str).str.zfill(6)

    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        combined.to_excel(writer, sheet_name="전체", index=False)
        for df, label in zip(dfs, ["투자주의", "투자경고", "투자위험"]):
            df[["분류", "code", "code_name", "reason", "post_date", "fix_date", "cleared_date"]].to_excel(
                writer, sheet_name=label, index=False)
    conn.close()
    print(f"저장 완료: {out} (전체 {len(combined)}행)")

if __name__ == '__main__':
    main()
