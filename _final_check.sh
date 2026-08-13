#!/bin/bash
echo "=== daily_craw 데이터 상태 ==="
mysql -u bot -pnastar79 -h 127.0.0.1 -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='daily_craw'" 2>/dev/null | xargs echo "테이블 수:"
mysql -u bot -pnastar79 -h 127.0.0.1 -N -e "SELECT COUNT(DISTINCT date), MIN(date), MAX(date) FROM daily_craw.\`삼성전자\`" 2>/dev/null | awk '{print "삼성전자:", $1"일 ("$2" ~ "$3")"}'

echo ""
echo "=== daily_buy_list 상태 ==="
mysql -u bot -pnastar79 -h 127.0.0.1 -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='daily_buy_list' AND table_name REGEXP '^[0-9]{8}$'" 2>/dev/null | xargs echo "날짜 테이블 수:"
mysql -u bot -pnastar79 -h 127.0.0.1 -N -e "SELECT MIN(table_name), MAX(table_name) FROM information_schema.tables WHERE table_schema='daily_buy_list' AND table_name REGEXP '^[0-9]{8}$'" 2>/dev/null | awk '{print "범위:", $1" ~ "$2}'

echo ""
echo "=== min_craw 상태 ==="
mysql -u bot -pnastar79 -h 127.0.0.1 -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='min_craw'" 2>/dev/null | xargs echo "테이블 수:"

echo ""
echo "=== 디스크 여유 ==="
df -h / | tail -1 | awk '{print "전체:"$2" 사용:"$3" 여유:"$4" ("$5")"}'
