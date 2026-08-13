# find_missing_tables.ps1
# 덤프 파일의 daily_craw 테이블 목록 vs 로컬 MySQL daily_craw 테이블 목록을 비교
$dumpPath = "C:\Users\UserK\Desktop\bot2\dump\bot2_dump_20260813.sql"

$dumpTables = New-Object 'System.Collections.Generic.HashSet[string]'
$inDailyCraw = $false
$reader = New-Object System.IO.StreamReader($dumpPath)
while ($null -ne ($line = $reader.ReadLine())) {
    if ($line -match '^USE `([^`]+)`') {
        $inDailyCraw = ($Matches[1] -eq 'daily_craw')
        continue
    }
    if ($inDailyCraw -and $line -match '^CREATE TABLE `([^`]+)`') {
        [void]$dumpTables.Add($Matches[1])
    }
}
$reader.Close()
Write-Host "dump  daily_craw tables : $($dumpTables.Count)"

$mysql = (Get-Command mysql -ErrorAction SilentlyContinue).Source
if (-not $mysql) {
    foreach ($c in @("C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe",
                     "C:\Program Files\MySQL\MySQL Server 5.7\bin\mysql.exe")) {
        if (Test-Path $c) { $mysql = $c; break }
    }
}
if (-not $mysql) { Write-Host "mysql client not found" -ForegroundColor Red; exit 1 }

$localRaw = & $mysql -h 127.0.0.1 -u bot -pnastar79 -N -e "SELECT table_name FROM information_schema.tables WHERE table_schema='daily_craw';" 2>$null
$localSet = New-Object 'System.Collections.Generic.HashSet[string]'
foreach ($t in $localRaw) {
    if ($t) { [void]$localSet.Add($t.Trim()) }
}
Write-Host "local daily_craw tables : $($localSet.Count)"

# 서버(덤프)에 있는데 로컬에 없는 테이블
$missing = @($dumpTables | Where-Object { -not $localSet.Contains($_) })
Write-Host ""
Write-Host "=== MISSING on local ($($missing.Count)) ==="
$missing | Sort-Object | ForEach-Object { $_ }
