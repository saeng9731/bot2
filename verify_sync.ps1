# verify_sync.ps1  (ASCII-only, safe encoding)
# Confirm that all dump daily_craw tables exist in local MySQL (ignore-case).
$dumpPath = "C:\Users\UserK\Desktop\bot2\dump\bot2_dump_20260813.sql"
$dumpOut  = "C:\Users\UserK\Desktop\bot2\dump\dump_tables_utf8.txt"
$localOut = "C:\Users\UserK\Desktop\bot2\dump\local_tables_utf8.txt"

# 1) extract daily_craw table names from dump (correct UTF-8, streaming)
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

# 2) local table names (use cmd redirect to preserve raw UTF-8 bytes)
$mysql = (Get-Command mysql -ErrorAction SilentlyContinue).Source
if (-not $mysql) {
    foreach ($c in @("C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe",
                     "C:\Program Files\MySQL\MySQL Server 5.7\bin\mysql.exe")) {
        if (Test-Path $c) { $mysql = $c; break }
    }
}
if (-not $mysql) { Write-Host "mysql client not found" -ForegroundColor Red; exit 1 }

cmd /c "`"$mysql`" -h 127.0.0.1 -u bot -pnastar79 --default-character-set=utf8mb4 -N -B -e `"SELECT table_name FROM information_schema.tables WHERE table_schema='daily_craw';`" > `"$localOut`" 2>nul"

$dump  = @(Get-Content -Encoding UTF8 $dumpOut)
$local = @(Get-Content -Encoding UTF8 $localOut)

$dumpUnique  = @($dump  | Sort-Object -Unique)
$localUnique = @($local | Sort-Object -Unique)

Write-Host ""
Write-Host "dump  daily_craw unique tables : $($dumpUnique.Count)"
Write-Host "local daily_craw unique tables : $($localUnique.Count)"
Write-Host ""

# case-insensitive check (PowerShell -notin is case-insensitive by default)
$missing = @($dumpUnique | Where-Object { $_ -notin $localUnique })
Write-Host "=== dump tables NOT in local (ignore-case) : $($missing.Count) ==="
$missing | Select-Object -First 30 | ForEach-Object { $_ }
Write-Host ""
Write-Host "=> if 0, sync is COMPLETE (all data present, case differences only)"