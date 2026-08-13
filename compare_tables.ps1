# compare_tables.ps1
# 덤프 파일의 daily_craw 테이블 목록 vs 로컬 MySQL daily_craw 테이블 목록 비교 (파일 기반)
$dumpPath = "C:\Users\UserK\Desktop\bot2\dump\bot2_dump_20260813.sql"
$dumpOut  = "C:\Users\UserK\Desktop\bot2\dump\dump_daily_craw_tables.txt"
$localOut = "C:\Users\UserK\Desktop\bot2\dump\local_daily_craw_tables.txt"

# 1) 덤프에서 daily_craw 테이블 이름 추출 (스트리밍)
$in = $false
$writer = New-Object System.IO.StreamWriter($dumpOut, $false, (New-Object System.Text.UTF8Encoding($false)))
$reader = New-Object System.IO.StreamReader($dumpPath)
while ($null -ne ($line = $reader.ReadLine())) {
    if ($line -match '^USE `([^`]+)`') {
        $in = ($Matches[1] -eq 'daily_craw')
        continue
    }
    if ($in -and $line -match '^CREATE TABLE `([^`]+)`') {
        $writer.WriteLine($Matches[1])
    }
}
$reader.Close(); $writer.Close()

# 2) 로컬 테이블 이름 추출
$mysql = (Get-Command mysql -ErrorAction SilentlyContinue).Source
if (-not $mysql) {
    foreach ($c in @("C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe",
                     "C:\Program Files\MySQL\MySQL Server 5.7\bin\mysql.exe")) {
        if (Test-Path $c) { $mysql = $c; break }
    }
}
if (-not $mysql) { Write-Host "mysql client not found" -ForegroundColor Red; exit 1 }
& $mysql -h 127.0.0.1 -u bot -pnastar79 -N -e "SELECT table_name FROM information_schema.tables WHERE table_schema='daily_craw' ORDER BY table_name;" 2>$null |
    Set-Content -Path $localOut -Encoding UTF8

$dump  = @(Get-Content $dumpOut)
$local = @(Get-Content $localOut)
Write-Host "dump  : $($dump.Count)  local : $($local.Count)"

# 3) 대소문자 구분 비교 (리눅스 서버 대소문자 구분 반영)
$miss1 = @(Compare-Object -CaseSensitive $dump $local | Where-Object { $_.SideIndicator -eq '<=' })
Write-Host ""
Write-Host "=== dump-only (MISSING, case-sensitive) : $($miss1.Count) ==="
$miss1 | ForEach-Object { $_.InputObject }
Write-Host ""

# 4) 대소문자 무시 비교
$miss2 = @(Compare-Object $dump $local | Where-Object { $_.SideIndicator -eq '<=' })
Write-Host "=== dump-only (MISSING, ignore-case) : $($miss2.Count) ==="
$miss2 | ForEach-Object { $_.InputObject }
Write-Host ""

# 5) 로컬에만 있는 (dump에 없는) 테이블
$miss3 = @(Compare-Object $dump $local | Where-Object { $_.SideIndicator -eq '=>' })
Write-Host "=== local-only (dump에는 없음) : $($miss3.Count) ==="
$miss3 | ForEach-Object { $_.InputObject }
