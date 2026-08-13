# -*- coding: utf-8 -*-
"""
서버 패치 스크립트 (v2)
==================================================
[수정 사항]
1. daily_buy_list.py
   - date_rows_setting() 에 gs글로벌 테이블 없을 때 fallback 추가

2. simulator_func_mysql.py
   - get_date_for_simul() 에 gs글로벌 테이블 없을 때 fallback 추가
   - dialect.has_table() → inspect().has_table() (SQLAlchemy 2.0 호환)

3. collector_api.py
   - dialect.has_table() → inspect().has_table() (SQLAlchemy 2.0 호환)
   - timedelta → datetime.timedelta 로 수정
   - from sqlalchemy import inspect 추가

[실행]
python patch_server.py
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

print("========================================")
print("서버 패치 스크립트 v2 시작")
print("========================================")

# ==============================================================
# 1. daily_buy_list.py 패치
# ==============================================================
dbl_path = os.path.join(BASE_DIR, "library", "daily_buy_list.py")

old_date_rows_setting = '''    def date_rows_setting(self):
        print("date_rows_setting!!")
        # 날짜 지정
        sql = "select date from `gs글로벌` where date >= '%s' group by date"
        self.date_rows = self.engine_daily_craw.execute(sql % self.start_date).fetchall()'''

new_date_rows_setting = '''    def date_rows_setting(self):
        print("date_rows_setting!!")
        # 날짜 지정
        try:
            sql = "select date from `gs글로벌` where date >= '%s' group by date"
            self.date_rows = self.engine_daily_craw.execute(sql % self.start_date).fetchall()
        except Exception:
            # gs글로벌 테이블이 없으면 (최초 실행 시) daily_craw DB의 다른 테이블에서 날짜 조회
            sql = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'daily_craw' LIMIT 1"
            table = self.engine_daily_craw.execute(sql).fetchall()
            if table:
                sql = "select date from `%s` where date >= '%s' group by date"
                self.date_rows = self.engine_daily_craw.execute(sql % (table[0][0], self.start_date)).fetchall()
            else:
                self.date_rows = []
                print("daily_craw DB에 테이블이 없습니다. daily_buy_list 생성을 건너뜁니다.")'''

with open(dbl_path, "r", encoding="utf-8") as f:
    dbl_content = f.read()

if old_date_rows_setting in dbl_content:
    dbl_content = dbl_content.replace(old_date_rows_setting, new_date_rows_setting)
    with open(dbl_path, "w", encoding="utf-8") as f:
        f.write(dbl_content)
    print("[OK] library/daily_buy_list.py - date_rows_setting() fallback 추가")
else:
    print("[SKIP] library/daily_buy_list.py - 이미 패치됨")

# ==============================================================
# 2. simulator_func_mysql.py 패치
# ==============================================================
sfm_path = os.path.join(BASE_DIR, "library", "simulator_func_mysql.py")

with open(sfm_path, "r", encoding="utf-8") as f:
    sfm_content = f.read()

# 2-1. inspect import 추가
if "from sqlalchemy import create_engine, inspect" not in sfm_content:
    if "from sqlalchemy import create_engine" in sfm_content:
        sfm_content = sfm_content.replace(
            "from sqlalchemy import create_engine",
            "from sqlalchemy import create_engine, inspect"
        )
        print("[OK] library/simulator_func_mysql.py - inspect import 추가")
    else:
        print("[WARN] library/simulator_func_mysql.py - create_engine import 패턴을 찾을 수 없음")

# 2-2. get_date_for_simul() fallback 추가
old_get_date_for_simul = '''    def get_date_for_simul(self):
        sql = "select date from `gs글로벌` where date >= '%s' and date <= '%s' group by date"
        self.date_rows = self.engine_daily_craw.execute(sql % (self.simul_start_date, self.simul_end_date)).fetchall()'''

new_get_date_for_simul = '''    def get_date_for_simul(self):
        try:
            sql = "select date from `gs글로벌` where date >= '%s' and date <= '%s' group by date"
            self.date_rows = self.engine_daily_craw.execute(sql % (self.simul_start_date, self.simul_end_date)).fetchall()
        except Exception:
            # gs글로벌 테이블이 없으면 (최초 실행 시) daily_craw DB의 다른 테이블에서 날짜 조회
            sql = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'daily_craw' LIMIT 1"
            table = self.engine_daily_craw.execute(sql).fetchall()
            if table:
                sql = "select date from `%s` where date >= '%s' and date <= '%s' group by date"
                self.date_rows = self.engine_daily_craw.execute(
                    sql % (table[0][0], self.simul_start_date, self.simul_end_date)).fetchall()
            else:
                self.date_rows = []
                print("daily_craw DB에 테이블이 없습니다. 시뮬레이션 날짜를 가져올 수 없습니다.")'''

if old_get_date_for_simul in sfm_content:
    sfm_content = sfm_content.replace(old_get_date_for_simul, new_get_date_for_simul)
    print("[OK] library/simulator_func_mysql.py - get_date_for_simul() fallback 추가")
else:
    print("[SKIP] library/simulator_func_mysql.py - get_date_for_simul() 이미 패치됨")

# 2-3. dialect.has_table() → inspect().has_table()
sfm_replacements = [
    ('self.engine_simulator.dialect.has_table(self.engine_simulator, "realtime_daily_buy_list")',
     'inspect(self.engine_simulator).has_table("realtime_daily_buy_list")'),
    ("self.engine_simulator.dialect.has_table(self.engine_simulator, 'jango_data')",
     "inspect(self.engine_simulator).has_table('jango_data')"),
]
for old, new in sfm_replacements:
    if old in sfm_content:
        sfm_content = sfm_content.replace(old, new)
        print(f"[OK] library/simulator_func_mysql.py - {old.split('.')[-1]} → inspect() 변환")

with open(sfm_path, "w", encoding="utf-8") as f:
    f.write(sfm_content)

# ==============================================================
# 3. collector_api.py 패치
# ==============================================================
ca_path = os.path.join(BASE_DIR, "library", "collector_api.py")

with open(ca_path, "r", encoding="utf-8") as f:
    ca_content = f.read()

# 3-1. inspect import 추가
if "from sqlalchemy import Integer, Text, Float, String, inspect" not in ca_content:
    if "from sqlalchemy import Integer, Text, Float, String" in ca_content:
        ca_content = ca_content.replace(
            "from sqlalchemy import Integer, Text, Float, String",
            "from sqlalchemy import Integer, Text, Float, String, inspect"
        )
        print("[OK] library/collector_api.py - inspect import 추가")
    else:
        print("[WARN] library/collector_api.py - sqlalchemy import 패턴을 찾을 수 없음")

# 3-2. timedelta → datetime.timedelta
if "datetime.date.today() - timedelta(days=10)" in ca_content:
    ca_content = ca_content.replace(
        "datetime.date.today() - timedelta(days=10)",
        "datetime.date.today() - datetime.timedelta(days=10)"
    )
    print("[OK] library/collector_api.py - timedelta → datetime.timedelta")

# 3-3. dialect.has_table() → inspect().has_table()
ca_replacements = [
    ('self.open_api.engine_daily_craw.dialect.has_table(self.open_api.engine_daily_craw, code_name)',
     'inspect(self.open_api.engine_daily_craw).has_table(code_name)'),
    ('self.open_api.engine_daily_buy_list.dialect.has_table(self.open_api.engine_daily_buy_list, dc_date)',
     'inspect(self.open_api.engine_daily_buy_list).has_table(dc_date)'),
    ('self.open_api.engine_daily_buy_list.dialect.has_table(self.open_api.engine_daily_buy_list, table_name)',
     'inspect(self.open_api.engine_daily_buy_list).has_table(table_name)'),
    ('self.open_api.engine_daily_craw.dialect.has_table(self.open_api.engine_daily_buy_list, row.tname)',
     'inspect(self.open_api.engine_daily_buy_list).has_table(row.tname)'),
]
for old, new in ca_replacements:
    if old in ca_content:
        ca_content = ca_content.replace(old, new)
        print(f"[OK] library/collector_api.py - dialect.has_table → inspect() 변환")

with open(ca_path, "w", encoding="utf-8") as f:
    f.write(ca_content)

print("")
print("========================================")
print("패치 완료! 이제 bash sh/collector.sh 를 다시 실행하세요.")
print("========================================")