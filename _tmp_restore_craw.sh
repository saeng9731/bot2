#!/bin/bash
# daily_craw 복원 스크립트
echo "=== 복원 전 daily_craw 테이블 수 ==="
mysql -u bot -pnastar79 -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='daily_craw';" 2>/dev/null

echo "=== 복원 시작: $(date) ==="
mysql -u bot -pnastar79 < /home/opc/bot2_daily_craw_dump.sql > /tmp/restore_craw.log 2>&1
echo "복원 종료 코드: $?"

echo "=== 복원 후 daily_craw 테이블 수 ==="
mysql -u bot -pnastar79 -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='daily_craw';" 2>/dev/null

echo "=== 삼성전자 데이터 확인 ==="
mysql -u bot -pnastar79 -N -e "SELECT COUNT(*), MIN(date), MAX(date) FROM daily_craw.\`삼성전자\`;" 2>/dev/null

echo "=== 완료: $(date) ==="
