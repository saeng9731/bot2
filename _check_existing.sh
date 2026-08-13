#!/bin/bash
echo "=== 서버 daily_craw에서 관련 테이블 확인 ==="
mysql -u bot -pnastar79 -h 127.0.0.1 -N -e "SELECT table_name FROM information_schema.tables WHERE table_schema='daily_craw' AND (table_name LIKE '%하이닉스%' OR table_name LIKE '%NAVER%' OR table_name LIKE '%LG전자%' OR table_name LIKE '%lg전자%' OR table_name LIKE '%naver%')" 2>/dev/null

echo ""
echo "=== 복원 전: 기존 테이블 데이터 수 ==="
for t in 'sk하이닉스' 'NAVER' 'LG전자' 'lg전자'; do
    cnt=$(mysql -u bot -pnastar79 -h 127.0.0.1 -N -e "SELECT COUNT(*) FROM daily_craw.\`$t\`" 2>/dev/null)
    echo "  $t: $cnt 행"
done
