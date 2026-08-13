#!/bin/bash
echo "=== 삼성전자 (덤프 복원 종목) ==="
mysql -u bot -pnastar79 -h 127.0.0.1 -N -e "SELECT COUNT(DISTINCT date), MIN(date), MAX(date) FROM daily_craw.\`삼성전자\`" 2>/dev/null | awk '{print "  일수:"$1" ("$2" ~ "$3")"}'

echo "=== SK하이닉스 (덤프에 없던 종목 - 600일부터 수집 중) ==="
mysql -u bot -pnastar79 -h 127.0.0.1 -N -e "SELECT COUNT(DISTINCT date), MIN(date), MAX(date) FROM daily_craw.\`SK하이닉스\`" 2>/dev/null | awk '{print "  일수:"$1" ("$2" ~ "$3")"}' || echo "  아직 테이블 없음"

echo "=== 콜렉터가 새로 추가한 데이터 확인 (20260731 이후) ==="
mysql -u bot -pnastar79 -h 127.0.0.1 -N -e "SELECT MAX(date) FROM daily_craw.\`삼성전자\` WHERE date > '20260731'" 2>/dev/null | xargs echo "  삼성전자 20260731 이후 최대날짜:"

echo "=== 진행 상태 ==="
ps -ef | grep collector_v3 | grep -v grep | awk '{print "  PID:"$2" 실행중"}'
