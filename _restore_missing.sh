#!/bin/bash
cd /home/opc/bot2
source /home/opc/new_autobot_env_py311/bin/activate

DB_ID=$(python -c "from library import cf; print(cf.db_id)")
DB_PW=$(python -c "from library import cf; print(cf.db_passwd)")

echo "=== 복원 시작: $(date) ==="
mysql -u "$DB_ID" -p"$DB_PW" -h 127.0.0.1 daily_craw < /home/opc/bot2/missing_stocks.sql
echo "=== 복원 완료: $(date) ==="

echo ""
echo "=== 복원 확인 ==="
for t in SK하이닉스 NAVER LG전자; do
    cnt=$(mysql -u "$DB_ID" -p"$DB_PW" -h 127.0.0.1 -N -e "SELECT COUNT(DISTINCT date), MIN(date), MAX(date) FROM daily_craw.\`$t\`" 2>/dev/null)
    echo "  $t: $cnt"
done
