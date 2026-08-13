# ============================================================
#  sync_server_to_windows.ps1
#  오라클 클라우드 서버(mydeal)에서 콜렉터가 모아둔 데이터를
#  윈도우 로컬 MySQL(바탕화면 bot 용)로 전송 + 복원합니다.
#
#  사용법
#    1) 아래 [설정]에서 SERVER_IP 와 SSH_KEY 만 채운다
#    2) 실행 (Windows PowerShell):
#         powershell -ExecutionPolicy Bypass -File sync_server_to_windows.ps1
#
#  ※ 참고
#    - "어제까지" = 서버 콜렉터가 어제까지 수집한 데이터.
#      daily_buy_list 의 오늘 이후 날짜 테이블은 덤프에서 자동 제외됩니다.
#    - daily_craw / min_craw 는 오늘 행이 없을 것(어제까지 수집)이라 그대로 포함.
# ============================================================

# ─────────────────────────────────────────
# [설정]  여기만 수정하면 됩니다
# ─────────────────────────────────────────
$SERVER_IP = "168.107.13.138"      # ← 오라클 서버 IP
$SSH_USER  = "opc"
$SSH_PORT  = 22
$SSH_KEY   = "C:\Users\UserK\Desktop\opc3..4\ssh-key-2026-02-24.key"   # ← SSH 개인키 파일 경로 (FileZilla autobot2 설정 기준)

$REMOTE_MYSQL_USER = "bot"
$REMOTE_MYSQL_PW   = "nastar79"

$LOCAL_MYSQL_HOST = "127.0.0.1"
$LOCAL_MYSQL_USER = "bot"
$LOCAL_MYSQL_PW   = "nastar79"

$LOCAL_DUMP_DIR = "C:\Users\UserK\Desktop\bot2\dump"   # 덤프를 받아둘 폴더
$MODE = "replace"   # "replace" = 로컬 4개 DB 교체 / "merge" = 기존 데이터 유지 + 추가
# ─────────────────────────────────────────

# $ErrorActionPreference = "Stop"  → 사용 안 함.
# mysql/ssh 같은 외부 프로그램이 stderr로 경고를 출력하면 "Stop" 설정 때문에
# 스크립트가 중단됩니다. 오류 판단은 각 단계의 $LASTEXITCODE 로 합니다.

# 0) 필수 정보 확인
if ([string]::IsNullOrWhiteSpace($SERVER_IP)) {
    Write-Host "[오류] SERVER_IP(오라클 서버 IP)가 비어 있습니다. 스크립트 상단 [설정]을 채워주세요." -ForegroundColor Red
    exit 1
}

# SSH 개인키 자동 탐색 (못 찾으면 직접 입력)
if ([string]::IsNullOrWhiteSpace($SSH_KEY)) {
    $candidateKeys = @(
        "$env:USERPROFILE\.ssh\id_rsa",
        "$env:USERPROFILE\.ssh\id_ed25519",
        "$env:USERPROFILE\.ssh\oci_key",
        "$env:USERPROFILE\.ssh\id_rsa.ppk"
    )
    $SSH_KEY = $candidateKeys | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if ([string]::IsNullOrWhiteSpace($SSH_KEY) -or -not (Test-Path $SSH_KEY)) {
    Write-Host "[오류] SSH 개인키를 찾지 못했습니다. 스크립트 상단 SSH_KEY에 키 파일 경로를 직접 입력하세요." -ForegroundColor Red
    exit 1
}

# 1) ssh / scp / mysql 클라이언트 찾기
$ssh   = (Get-Command ssh -ErrorAction SilentlyContinue).Source
$scp   = (Get-Command scp -ErrorAction SilentlyContinue).Source
$mysql = (Get-Command mysql -ErrorAction SilentlyContinue).Source
if (-not $mysql) {
    foreach ($c in @("C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe",
                     "C:\Program Files\MySQL\MySQL Server 5.7\bin\mysql.exe")) {
        if (Test-Path $c) { $mysql = $c; break }
    }
}
if (-not $ssh)  { Write-Host "[오류] ssh 명령이 없습니다 (Windows OpenSSH 필요)." -ForegroundColor Red; exit 1 }
if (-not $scp)  { Write-Host "[오류] scp 명령이 없습니다 (Windows OpenSSH 필요)." -ForegroundColor Red; exit 1 }
if (-not $mysql){ Write-Host "[오류] 로컬 mysql 클라이언트를 찾지 못했습니다. MySQL 설치 경로를 확인하세요." -ForegroundColor Red; exit 1 }

# 2) 날짜/파일명/폴더 준비
$today      = Get-Date -Format "yyyyMMdd"
$yesterday  = (Get-Date).AddDays(-1).ToString("yyyyMMdd")
$dumpName   = "bot2_dump_$today.sql"
$remoteDump = "/home/opc/$dumpName"
$remoteSh   = "server_dump_remote_$today.sh"
if (-not (Test-Path $LOCAL_DUMP_DIR)) { New-Item -ItemType Directory -Path $LOCAL_DUMP_DIR | Out-Null }

Write-Host ""
Write-Host "============================================================"
Write-Host " 서버($SERVER_IP) -> 윈도우 DB 동기화 시작  [$MODE 모드]"
Write-Host " 대상: daily_craw / min_craw / daily_buy_list / JackBot11_imi1"
Write-Host " 기준: 어제($yesterday)까지 수집분 (오늘 이후 daily_buy_list 테이블 제외)"
Write-Host " 덤프 파일: $dumpName"
Write-Host "============================================================"

# 3) 로컬 MySQL 접속 확인 (스크립트 초반에 미리 체크)
Write-Host "[0/4] 로컬 MySQL 접속 확인..."
& $mysql -h $LOCAL_MYSQL_HOST -u $LOCAL_MYSQL_USER "-p$LOCAL_MYSQL_PW" -e "SELECT 1;" 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[오류] 로컬 MySQL 접속 실패. 로컬 MySQL 서비스 실행 여부와 계정/비밀번호를 확인하세요." -ForegroundColor Red
    exit 1
}
Write-Host "      로컬 MySQL 접속 OK" -ForegroundColor Green

# 4) 원격 덤프용 셸 스크립트 생성
$dumpOptions = "--single-transaction --routines --triggers --databases daily_craw min_craw daily_buy_list JackBot11_imi1"
if ($MODE -eq "merge") {
    $dumpOptions = "--skip-add-drop-table --skip-add-locks " + $dumpOptions
}

$remoteScript = @"
#!/bin/bash
set -e
echo "=== [원격] 콜렉터 데이터 덤프 시작: `$(date) ==="
TODAY="$today"
IGNORE=""
# daily_buy_list 에서 오늘 이후 날짜 테이블 제외 (어제까지 데이터만 덤프)
for t in `$(mysql -u $REMOTE_MYSQL_USER -p$REMOTE_MYSQL_PW -N -e "SELECT table_name FROM information_schema.tables WHERE table_schema='daily_buy_list' AND table_name REGEXP '^[0-9]{8}`$' AND table_name >= '$TODAY'"); do
    IGNORE="`$IGNORE --ignore-table=daily_buy_list.`$t"
done
echo "[원격] 오늘(`$TODAY) 이후 daily_buy_list 제외 테이블:`$IGNORE"
if [ -n "`$IGNORE" ]; then
    mysqldump -u $REMOTE_MYSQL_USER -p$REMOTE_MYSQL_PW $dumpOptions `$IGNORE > $remoteDump
else
    mysqldump -u $REMOTE_MYSQL_USER -p$REMOTE_MYSQL_PW $dumpOptions > $remoteDump
fi
ls -lh $remoteDump
echo "=== [원격] 덤프 완료 ==="
"@

$remoteScriptLocal = "$LOCAL_DUMP_DIR\$remoteSh"
$content = $remoteScript -replace "`r`n", "`n"
[System.IO.File]::WriteAllText($remoteScriptLocal, $content, (New-Object System.Text.UTF8Encoding($false)))

# 5) 원격 스크립트 업로드 → 실행
Write-Host "[1/4] 원격 덤프 스크립트 업로드..."
& $scp -i $SSH_KEY -P $SSH_PORT -o StrictHostKeyChecking=accept-new $remoteScriptLocal "$SSH_USER@${SERVER_IP}:/home/opc/$remoteSh"
if ($LASTEXITCODE -ne 0) { Write-Host "[오류] 스크립트 업로드 실패" -ForegroundColor Red; exit 1 }

Write-Host "[2/4] 서버에서 mysqldump 실행 (오래 걸릴 수 있음)..."
& $ssh -i $SSH_KEY -p $SSH_PORT -o StrictHostKeyChecking=accept-new -o BatchMode=yes "$SSH_USER@$SERVER_IP" "bash /home/opc/$remoteSh"
if ($LASTEXITCODE -ne 0) { Write-Host "[오류] 원격 덤프 실패" -ForegroundColor Red; exit 1 }

# 6) 덤프 파일 다운로드
Write-Host "[3/4] 덤프 파일 다운로드..."
& $scp -i $SSH_KEY -P $SSH_PORT -o StrictHostKeyChecking=accept-new "$SSH_USER@${SERVER_IP}:$remoteDump" "$LOCAL_DUMP_DIR\$dumpName"
if ($LASTEXITCODE -ne 0) { Write-Host "[오류] 덤프 다운로드 실패" -ForegroundColor Red; exit 1 }

# 7) 로컬 MySQL 복원
Write-Host "[4/4] 로컬 MySQL 복원 ($MODE 모드)..."
$sqlFile     = "$LOCAL_DUMP_DIR\$dumpName"
$sqlFileSlash = ($sqlFile -replace '\\', '/')

if ($MODE -eq "replace") {
    foreach ($db in @("daily_craw","min_craw","daily_buy_list","JackBot11_imi1")) {
        & $mysql -h $LOCAL_MYSQL_HOST -u $LOCAL_MYSQL_USER "-p$LOCAL_MYSQL_PW" -e "DROP DATABASE IF EXISTS $db; CREATE DATABASE IF NOT EXISTS $db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        if ($LASTEXITCODE -ne 0) { Write-Host "[오류] DB 초기화 실패: $db" -ForegroundColor Red; exit 1 }
    }
    & $mysql -h $LOCAL_MYSQL_HOST -u $LOCAL_MYSQL_USER "-p$LOCAL_MYSQL_PW" -e "source $sqlFileSlash"
    if ($LASTEXITCODE -ne 0) { Write-Host "[오류] 복원 실패 (replace)" -ForegroundColor Red; exit 1 }
}
elseif ($MODE -eq "merge") {
    # INSERT INTO -> INSERT IGNORE INTO 로 치환 (기존 행은 유지, 새 행만 추가)
    $mergedFile  = $sqlFile -replace '\.sql$', '_merge.sql'
    $mergedSlash = ($mergedFile -replace '\\', '/')
    $reader = New-Object System.IO.StreamReader($sqlFile)
    $writer = New-Object System.IO.StreamWriter($mergedFile, $false, (New-Object System.Text.UTF8Encoding($false)))
    while ($null -ne ($line = $reader.ReadLine())) {
        # 기존 테이블이 있으면 그대로 두고(구조 오류 방지), 기존 행은 유지한 채 새 행만 추가
        if ($line -like '*INSERT INTO*') { $line = $line -replace 'INSERT INTO', 'INSERT IGNORE INTO' }
        if ($line -like '*CREATE TABLE *') { $line = $line -replace 'CREATE TABLE ', 'CREATE TABLE IF NOT EXISTS ' }
        $writer.WriteLine($line)
    }
    $reader.Close(); $writer.Close()
    & $mysql -h $LOCAL_MYSQL_HOST -u $LOCAL_MYSQL_USER "-p$LOCAL_MYSQL_PW" -e "source $mergedSlash"
    if ($LASTEXITCODE -ne 0) { Write-Host "[오류] 복원 실패 (merge)" -ForegroundColor Red; exit 1 }
}
else {
    Write-Host "[오류] MODE 는 replace 또는 merge 만 가능합니다. 현재: $MODE" -ForegroundColor Red
    exit 1
}

# 8) 검증
Write-Host ""
Write-Host "=== 복원 검증 ===" -ForegroundColor Green
& $mysql -h $LOCAL_MYSQL_HOST -u $LOCAL_MYSQL_USER "-p$LOCAL_MYSQL_PW" -N -e 'SELECT CONCAT("daily_craw 테이블 수: ", COUNT(*)) FROM information_schema.tables WHERE table_schema="daily_craw";'
& $mysql -h $LOCAL_MYSQL_HOST -u $LOCAL_MYSQL_USER "-p$LOCAL_MYSQL_PW" -N -e 'SELECT CONCAT("삼성전자 일봉: ", COUNT(DISTINCT date), "일 (", MIN(date), " ~ ", MAX(date), ")") FROM daily_craw.`삼성전자`;'
& $mysql -h $LOCAL_MYSQL_HOST -u $LOCAL_MYSQL_USER "-p$LOCAL_MYSQL_PW" -N -e 'SELECT CONCAT("daily_buy_list 최신 날짜 테이블: ", MAX(table_name)) FROM information_schema.tables WHERE table_schema="daily_buy_list" AND table_name REGEXP "^[0-9]{8}$";'

Write-Host ""
Write-Host "============================================================"
Write-Host " 완료! 덤프 파일: $LOCAL_DUMP_DIR\$dumpName"
Write-Host " (서버 /home/opc/$dumpName 에도 동일한 백업이 남아 있습니다)"
Write-Host "============================================================"

