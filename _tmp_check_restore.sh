#!/bin/bash
echo "=== 복원 진행 상태 ==="
ps aux | grep "mysql" | grep "bot2_daily" | grep -v grep || echo "복원 mysql 프로세스 없음(완료 또는 미실행)"

echo ""
echo "=== 복원 출력 로그 ==="
cat /tmp/restore_craw_out.log 2>/dev/null || echo "로그 없음"

echo ""
echo "=== daily_craw 테이블 수 ==="
mysql -u bot -pnastar79 -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='daily_craw';" 2>/dev/null

echo ""
echo "=== 삼성전자 확인 ==="
mysql -u bot -pnastar79 -N -e "SELECT COUNT(*), MIN(date), MAX(date) FROM daily_craw.\`삼성전자\`;" 2>/dev/null
