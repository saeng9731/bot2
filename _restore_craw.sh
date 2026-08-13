#!/bin/bash
cd /home/opc/bot2
source /home/opc/new_autobot_env_py311/bin/activate

DB_ID=$(python -c "from library import cf; print(cf.db_id)")
DB_PW=$(python -c "from library import cf; print(cf.db_passwd)")

echo "DB 계정: $DB_ID"
echo "=== 덤프 파일 확인 ==="
ls -lh /home/opc/bot2_daily_craw_dump.sql

echo "=== DB 권한 확인 (DROP/CREATE 가능한지) ==="
mysql -u "$DB_ID" -p"$DB_PW" -h 127.0.0.1 -e "SHOW GRANTS FOR CURRENT_USER;" 2>&1 | grep -i -E 'DROP|ALL|CREATE' | head -5

echo "=== 현재 daily_craw 테이블 수 ==="
mysql -u "$DB_ID" -p"$DB_PW" -h 127.0.0.1 -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='daily_craw';" 2>&1 | tail -1
