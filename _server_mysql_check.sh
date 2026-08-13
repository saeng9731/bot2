#!/bin/bash
# 서버 MySQL 상태 자세히 확인
echo "=== mysqld 프로세스 ==="
ps aux | grep -v grep | grep mysqld
echo ""
echo "=== 3306 리슨 ==="
ss -tln | grep 3306
echo ""
echo "=== TCP 127.0.0.1:3306 접속 ==="
mysql -u bot -pnastar79 -h 127.0.0.1 -P 3306 -N -e "SELECT @@hostname, @@port, @@datadir"
echo "-- DB 목록 --"
mysql -u bot -pnastar79 -h 127.0.0.1 -P 3306 -N -e "SHOW DATABASES"
echo "-- min_craw 테이블 수 --"
mysql -u bot -pnastar79 -h 127.0.0.1 -P 3306 -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='min_craw'"
echo ""
echo "=== 소켓 접속 ==="
mysql -u bot -pnastar79 -N -e "SELECT @@hostname, @@port, @@datadir"
echo "-- DB 목록 --"
mysql -u bot -pnastar79 -N -e "SHOW DATABASES"
echo "-- min_craw 테이블 수 --"
mysql -u bot -pnastar79 -N -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='min_craw'"
