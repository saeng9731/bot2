#!/bin/bash
# 복원 진행 상황 확인
mysql -u bot -pnastar79 -h 127.0.0.1 -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='daily_craw';" 2>/dev/null
