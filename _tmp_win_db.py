import pymysql

# 로컬 MySQL 접속 시도 (Windows 원본 데이터 확인)
try:
    con = pymysql.connect(
        host='localhost', port=3306, user='root', password='',
        charset='utf8mb4', connect_timeout=5
    )
    cur = con.cursor()
    cur.execute("show databases")
    dbs = [r[0] for r in cur.fetchall()]
    print('로컬 DB 목록:', dbs)
    con.close()
except Exception as e:
    print('root/비번없음 접속 실패:', e)
    # 다른 계정 시도
    for user, pwd in [('bot', 'nastar79'), ('root', 'nastar79'), ('root', 'root'), ('bot', '')]:
        try:
            con = pymysql.connect(
                host='localhost', port=3306, user=user, password=pwd,
                charset='utf8mb4', connect_timeout=5
            )
            cur = con.cursor()
            cur.execute("show databases")
            dbs = [r[0] for r in cur.fetchall()]
            print(f'{user}/{pwd} 접속 성공! DB 목록:', dbs)
            con.close()
            break
        except Exception as e2:
            print(f'{user}/{pwd} 실패:', str(e2)[:80])
