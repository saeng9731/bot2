#!/bin/bash
# ============================================================
#  dump_bot2.sh - mydeal(bot2 서버)에서 실행하는 백업 스크립트
#  bot2 MySQL 데이터 덤프 + 봇 프로세스 정지 + crontab 정리
#  실행 방법: bash dump_bot2.sh
# ============================================================
set -e

DB_ID="bot"
DB_PASSWD="${DB_PASSWD:-nastar79}"
DUMP_FILE="/home/opc/bot2_dump_$(date +%Y%m%d).sql"

echo "========================================================"
echo " bot2 데이터 백업 시작 (mydeal)"
echo "========================================================"

echo ""
echo "=== [1/4] 실행 중인 봇 프로세스 정지 ==="
pkill -f "collector_v3.py" 2>/dev/null || true
pkill -f "kind_crawling.py" 2>/dev/null || true
pkill -f "trader.py" 2>/dev/null || true
sleep 2
echo "프로세스 정지 완료"

echo ""
echo "=== [2/4] crontab 백업 + bot2 항목 주석 처리 ==="
crontab -l > /home/opc/crontab_before_migrate_$(date +%Y%m%d).txt 2>/dev/null || true
# 'bot2' 포함 항목 앞에 # 추가 (이중 실행 방지)
crontab -l 2>/dev/null | sed -e 's|^\([^#].*bot2.*\)|#\1|' | crontab - || true
echo "crontab bot2 항목 주석 처리 완료 (백업: crontab_before_migrate_*.txt)"

echo ""
echo "=== [3/4] MySQL 덤프 ==="
echo "덤프 파일: $DUMP_FILE"
mysqldump -u "$DB_ID" -p"$DB_PASSWD" --single-transaction --routines --triggers \
  --databases daily_craw min_craw daily_buy_list JackBot11_imi1 \
  > "$DUMP_FILE"
echo "덤프 완료!"
ls -lh "$DUMP_FILE"

echo ""
echo "=== [4/4] 완료 안내 ==="
echo ""
echo "덤프 파일 위치 : $DUMP_FILE"
echo ""
echo "다음 단계:"
echo "  1) FileZilla로 $DUMP_FILE 을 내 PC로 다운로드"
echo "  2) 다시 FileZilla로 mydeal3에 업로드"
echo "  3) mydeal3에서 restore_bot2.sh 실행"
echo ""
echo "※ crontab 복구가 필요하면: crontab /home/opc/crontab_before_migrate_$(date +%Y%m%d).txt"
echo "========================================================"
