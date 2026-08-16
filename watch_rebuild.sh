#!/bin/bash
# watch_rebuild.sh - daily_buy_list 재구축 완료 후 시뮬 크론 자동 복원
LOG=/home/opc/bot2/log/daily_buy_list_rebuild.log
echo "[$(date '+%Y-%m-%d %H:%M:%S')] watchdog 시작: daily_buy_list 재구축 완료 대기" >> $LOG

while pgrep -f "daily_buy_list" > /dev/null 2>&1; do
    sleep 300
done

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 재구축 종료 감지 → 시뮬 크론 복원" >> $LOG
crontab -l | sed '/simul_run\.sh/ s/^#//' | crontab -
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 복원 후 상태:" >> $LOG
crontab -l | grep simul_run >> $LOG
echo "[$(date '+%Y-%m-%d %H:%M:%S')] watchdog 완료 (시뮬은 다음 15:00 UTC부터 시작)" >> $LOG
