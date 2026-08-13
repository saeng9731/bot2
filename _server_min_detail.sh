#!/bin/bash
# min_craw 불일치 원인 확인
echo "=== SHOW TABLES FROM min_craw ==="
mysql -u bot -pnastar79 -N -e "SHOW TABLES FROM min_craw" 2>/dev/null | head -30
echo ""
echo "=== SHOW TABLES FROM min_craw 줄 수 ==="
mysql -u bot -pnastar79 -N -e "SHOW TABLES FROM min_craw" 2>/dev/null | wc -l
echo ""
echo "=== information_schema min_craw 테이블 수 ==="
mysql -u bot -pnastar79 -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='min_craw'" 2>/dev/null
echo ""
echo "=== /var/lib/mysql/min_craw 디렉토리 ==="
ls -la /var/lib/mysql/min_craw/ 2>/dev/null | head -20
echo ""
echo "=== /var/lib/mysql/min_craw 파일 개수 ==="
ls /var/lib/mysql/min_craw/ 2>/dev/null | wc -l
echo ""
echo "=== DB 목록 (information_schema.schemata) ==="
mysql -u bot -pnastar79 -N -e "SELECT SCHEMA_NAME FROM information_schema.schemata" 2>/dev/null
