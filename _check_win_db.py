import pymysql

conn = pymysql.connect(host='127.0.0.1', user='bot', password='nastar79', db='daily_craw', charset='utf8mb4')
cur = conn.cursor()

# 확인할 종목들
stocks = ['SK하이닉스', 'NAVER', '현대자동차', 'LG전자', '삼성전자']

print("=== 윈도우 MySQL의 종목 데이터 일수 ===")
for s in stocks:
    try:
        cur.execute(f"SELECT COUNT(DISTINCT date), MIN(date), MAX(date) FROM `{s}`")
        cnt, mn, mx = cur.fetchone()
        print(f"  {s}: {cnt}일 ({mn} ~ {mx})")
    except Exception as e:
        print(f"  {s}: 없음 ({type(e).__name__})")

# 서버에 없는 종목 전체 목록 (윈도우 기준으로 확인)
print("\n=== 윈도우 daily_craw 전체 테이블 수 ===")
cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='daily_craw'")
print(f"  윈도우: {cur.fetchone()[0]}개")

conn.close()
