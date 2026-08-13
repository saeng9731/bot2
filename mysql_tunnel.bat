@echo off
REM ============================================================
REM  MySQL SSH Tunnel:  localhost:3307 -> remote localhost:3306
REM  Server: opc@168.107.13.138  (Oracle Cloud, hostname: mydeal3)
REM  Usage : double-click or run, Ctrl+C to stop.
REM  Note  : plink(PuTTY 0.83) rejects OpenSSH-format key files,
REM          so we use the built-in Windows OpenSSH client (ssh.exe).
REM ============================================================
ssh -N -L 3307:localhost:3306 ^
    -i "C:\Users\UserK\Desktop\opc3..4\ssh-key-2026-02-24.key" ^
    -o ExitOnForwardFailure=yes ^
    -o ServerAliveInterval=30 ^
    -o ServerAliveCountMax=3 ^
    opc@168.107.13.138
pause
