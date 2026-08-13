#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
sh/fix_collation.py - MySQL 테이블 collation 통일 스크립트
(에러 1267 "Illegal mix of collations ... for operation '='" 해결)

사용법 (오라클 서버에서):
    cd /home/opc/bot2
    source /home/opc/new_autobot_env_py311/bin/activate
    python sh/fix_collation.py                        # daily_buy_list 만 처리
    python sh/fix_collation.py daily_buy_list simulator11 JackBot11_imi1  # 여러 DB 한번에

동작:
    1. 해당 DB에서 테이블이 가장 많은 collation(=주력)을 자동 판단
    2. 주력과 다른 collation을 가진 테이블들만 주력 collation으로 변환
    3. DB 기본 collation도 주력으로 통일 (앞으로 to_sql로 새로 만들어지는 테이블도 동일하게)

주의: daily_craw / min_craw 는 종목별 테이블이 수천 개라 변환에 시간이 오래 걸립니다.
      꼭 필요한 경우가 아니면 건드리지 마세요.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pymysql

from library import cf

DEFAULT_DBS = ['daily_buy_list']


def fix_db(cur, con, db_name, target=None):
    # 1) collation 분포 확인
    cur.execute("""
        SELECT table_collation, COUNT(*) FROM information_schema.tables
        WHERE table_schema = %s GROUP BY table_collation ORDER BY COUNT(*) DESC
    """, (db_name,))
    rows = cur.fetchall()
    if not rows:
        print(f"[{db_name}] 테이블이 없거나 DB가 없습니다. 건너뜁니다.")
        return

    print(f"[{db_name}] 현재 collation 분포: {rows}")

    # 2) 테이블 수가 가장 많은 collation을 기준으로
    if target is None:
        target = rows[0][0]
    print(f"[{db_name}] 통일 대상 collation: {target}")

    # 3) 주력과 다른 collation을 가진 테이블만 변환
    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = %s AND table_collation <> %s
    """, (db_name, target))
    tables = [r[0] for r in cur.fetchall()]

    for t in tables:
        sql = f"ALTER TABLE `{db_name}`.`{t}` CONVERT TO CHARACTER SET utf8mb4 COLLATE {target}"
        print(f"[{db_name}] ALTER TABLE `{t}` ...")
        cur.execute(sql)

    # 4) DB 기본 collation 통일 (새 테이블용)
    cur.execute(f"ALTER DATABASE `{db_name}` CHARACTER SET utf8mb4 COLLATE {target}")
    con.commit()
    print(f"[{db_name}] 완료 - 변경 테이블 {len(tables)}개")


def main():
    dbs = sys.argv[1:] or DEFAULT_DBS
    con = pymysql.connect(
        host=cf.db_ip, port=int(cf.db_port),
        user=cf.db_id, password=cf.db_passwd,
        charset='utf8mb4'
    )
    cur = con.cursor()
    for db in dbs:
        try:
            fix_db(cur, con, db)
        except Exception as e:
            print(f"[{db}] 오류 발생: {e}")
            con.rollback()
    con.close()
    print("모든 작업 완료")


if __name__ == '__main__':
    main()
