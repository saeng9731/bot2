#!/bin/bash
# watch_backfill.sh - 분봉 백필 완료를 감지해 min_craw 크론을 자동 복원
LOG=/home/opc/bot2/log/min_craw_backfill_1yr.log

echo "[$(date '+%Y-%m-%d %H:%M:%S')] watchdog 시작: 백필 완료 대기 중" >> $LOG

# 1) 백필 프로세스가 끝날 때까지 5분 간격 대기
while pgrep -f "min_craw_backfill.py" > /dev/null 2>&1; do
    sleep 300
done

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 백필 종료 감지 → 크론 복원" >> $LOG

# 2) min_craw.sh 크론 주석 해제 (복원)
crontab -l | sed '/min_craw\.sh/ s/^#//' | crontab -

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 복원 후 상태:" >> $LOG
crontab -l | grep min_craw >> $LOG
echo "[$(date '+%Y-%m-%d %H:%M:%S')] watchdog 완료" >> $LOG
