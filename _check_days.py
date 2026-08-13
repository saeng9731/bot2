import pymysql
pymysql.install_as_MySQLdb()
from sqlalchemy import create_engine, text
from library import cf

eng = create_engine(f"mysql+pymysql://{cf.db_id}:{cf.db_passwd}@{cf.db_ip}:{cf.db_port}/daily_craw")

for t in ['삼성전자', 'SK하이닉스', 'NAVER', '현대자동차']:
    try:
        cnt = eng.execute(text(f"SELECT COUNT(DISTINCT date) FROM `{t}`")).fetchone()[0]
        mx = eng.execute(text(f"SELECT MAX(date) FROM `{t}`")).fetchone()[0]
        mn = eng.execute(text(f"SELECT MIN(date) FROM `{t}`")).fetchone()[0]
        print(f"{t}: {cnt}일 ({mn} ~ {mx})")
    except Exception as e:
        print(f"{t}: 오류 {e}")
