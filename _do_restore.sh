#!/bin/bash
cd /home/opc/bot2
source /home/opc/new_autobot_env_py311/bin/activate

DB_ID=$(python -c "from library import cf; print(cf.db_id)")
DB_PW=$(python -c "from library import cf; print(cf.db_passwd)")

echo "[1/3] daily_craw DB 초기화..."
mysql -u "$DB_ID" -p"$DB_PW" -h 127.0.0.1 -e "DROP DATABASE IF EXISTS daily_craw; CREATE DATABASE daily_craw CHARACTER SET utf8mb4;"
echo "DB 초기화 완료"

echo "[2/3] 윈도우 덤프 복원 시작: $(date)"
mysql -u "$DB_ID" -p"$DB_PW" -h 127.0.0.1 daily_craw < /home/opc/bot2_daily_craw_dump.sql
echo "[3/3] 복원 완료: $(date)"

echo "=== 복원 확인 ==="
mysql -u "$DB_ID" -p"$DB_PW" -h 127.0.0.1 daily_craw -e "SELECT COUNT(*) AS 테이블수 FROM information_schema.tables WHERE table_schema='daily_craw';" 2>&1 | tail -1
mysql -u "$DB_ID" -p"$DB_PW" -h 127.0.0.1 daily_craw -e "SELECT COUNT(DISTINCT date) AS 일수, MIN(date) AS 시작, MAX(date) AS 끝 FROM \`삼성전자\`;" 2>&1 | tail -2
