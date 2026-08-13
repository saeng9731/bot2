import pymysql
import sys
import pandas as pd
sys.path.insert(0, '/home/opc/bot2')
from library import cf

# ai_filter와 동일한 방식: create_training_engine + pd.read_sql
tr_engine = pymysql.connect(
    host=cf.db_ip,
    port=int(cf.db_port),
    user=cf.db_id,
    password=cf.db_passwd,
    db='daily_craw',
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)

code_name = '삼성SDI'
until = '20260107'
feature_columns = ["close", "volume", "open", "high", "low"]
sql = """
    SELECT {} FROM `{}`
    WHERE STR_TO_DATE(date, '%Y%m%d%H%i') <= '{}'
""".format(','.join(feature_columns), code_name, until)

print('SQL:', sql)
df = pd.read_sql(sql, tr_engine)
print('pd.read_sql 결과 건수:', len(df))
print('컬럼:', list(df.columns))
if len(df) > 0:
    print('샘플:', df.head(3))
tr_engine.close()
