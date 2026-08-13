#!/bin/bash
# ============================================================
#  restore_bot2.sh - mydeal3(KIS 서버)에서 실행하는 복원 스크립트
#  setup_bot2.sh 실행 후, mydeal에서 만든 덤프 파일을 복원
#  실행 방법: bash restore_bot2.sh /home/opc/bot2_dump_YYYYMMDD.sql
# ============================================================
set -e

DUMP_FILE="${1:-/home/opc/bot2_dump.sql}"
DB_ID="bot"
DB_PASSWD="${DB_PASSWD:-nastar79}"

if [ ! -f "$DUMP_FILE" ]; then
    echo "[오류] 덤프 파일을 찾을 수 없습니다: $DUMP_FILE"
    echo "       사용법: bash restore_bot2.sh /home/opc/bot2_dump_20260807.sql"
    exit 1
fi

echo "========================================================"
echo " bot2 데이터 복원 시작 (mydeal3)"
echo " 덤프 파일: $DUMP_FILE"
echo "========================================================"

echo ""
echo "=== [1/3] MySQL 실행 확인 ==="
sudo systemctl start mysql 2>/dev/null || sudo service mysql start 2>/dev/null || true
if mysqladmin -u "$DB_ID" -p"$DB_PASSWD" ping >/dev/null 2>&1; then
    echo "MySQL 정상 동작 중 ✅"
else
    echo "[경고] MySQL 접속 실패 - setup_bot2.sh가 먼저 실행됐는지 확인하세요"
    echo "       sudo mysql -e \"ALTER USER 'bot'@'localhost' IDENTIFIED BY '${DB_PASSWD}'; FLUSH PRIVILEGES;\""
fi

echo ""
echo "=== [2/3] 덤프 복원 ==="
mysql -u "$DB_ID" -p"$DB_PASSWD" < "$DUMP_FILE"
echo "복원 완료 ✅"

echo ""
echo "=== [3/3] 데이터 검증 ==="
for db in daily_craw min_craw daily_buy_list JackBot11_imi1; do
    cnt=$(mysql -u "$DB_ID" -p"$DB_PASSWD" -N -e \
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$db';" 2>/dev/null || echo "0")
    echo "  - $db: 테이블 $cnt 개"
done

echo ""
echo "--- 삼성전자(005930) 일봉 데이터 수 (mydeal 결과와 비교!) ---"
mysql -u "$DB_ID" -p"$DB_PASSWD" -N -e "SELECT COUNT(*) FROM daily_craw.\`005930\`;" 2>/dev/null \
    && echo "  ↑ 위 숫자를 mydeal의 같은 쿼리 결과와 비교하세요"

echo ""
echo "========================================================"
echo " 복원 완료!"
echo ""
echo " 다음 (MobaXterm):"
echo "  1) source /home/opc/new_autobot_env_py311/bin/activate"
echo "  2) cd /home/opc/bot2"
echo "  3) python -c \"from library import cf; print(cf.db_ip)\"   # localhost 확인"
echo "  4) 장마감 후: python collector_v3.py   (1회 테스트)"
echo "  5) 로그: tail -f log/jackbot.log"
echo ""
echo " [중요] mydeal에서 bot2가 완전히 옮겨졌는지 확인 후에만 mydeal 삭제!"
echo "========================================================"
