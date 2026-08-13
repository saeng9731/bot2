#!/bin/bash
echo "=== 서버 daily_craw에서 해당 종목들의 실제 데이터 일수 확인 ==="
for t in 'sk하이닉스' 'naver' 'lg전자'; do
    res=$(mysql -u bot -pnastar79 -h 127.0.0.1 -N -e "SELECT COUNT(DISTINCT date), MIN(date), MAX(date) FROM daily_craw.\`$t\`" 2>/dev/null)
    echo "  $t: $res"
done
