import sys
import pandas as pd
sys.path.insert(0, '/home/opc/bot2')
from ai_filter import create_training_engine

tr_engine = create_training_engine('daily_craw')

code_name = '삼성SDI'
until = '20260107'
feature_columns = ["close", "volume", "open", "high", "low"]
sql = """
    SELECT {} FROM `{}`
    WHERE date <= '{}'
""".format(','.join(feature_columns), code_name, until)

df = pd.read_sql(sql, tr_engine)
print('건수:', len(df))
print('컬럼:', list(df.columns))
print('close 타입:', df['close'].dtype)
print('샘플:')
print(df.head(5))

