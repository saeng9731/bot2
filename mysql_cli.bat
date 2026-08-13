@echo off
REM ============================================================
REM  MySQL CLI 연결 (SSH 터널 경유)
REM  필수: mysql_tunnel.bat 으로 터널이 먼저 실행 중이어야 함
REM  접속 후 비밀번호 입력: nastar79
REM ============================================================
"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -h 127.0.0.1 -P 3307 -u bot -p
pause
