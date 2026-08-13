# count_dump_tables.ps1
# 덤프 파일(bot2_dump_YYYYMMDD.sql) 안의 DB별 CREATE TABLE 개수를 셉니다.
# 사용법: powershell -ExecutionPolicy Bypass -File count_dump_tables.ps1
$path = "C:\Users\UserK\Desktop\bot2\dump\bot2_dump_20260813.sql"

if (-not (Test-Path $path)) {
    Write-Host "dump file not found: $path" -ForegroundColor Red
    exit 1
}

$db = ""
$counts = @{}
$reader = New-Object System.IO.StreamReader($path)
while ($null -ne ($line = $reader.ReadLine())) {
    if ($line -match '^USE `([^`]+)`') {
        $db = $Matches[1]
        if (-not $counts.ContainsKey($db)) { $counts[$db] = 0 }
    }
    elseif ($line -match '^CREATE TABLE `') {
        if ($counts.ContainsKey($db)) { $counts[$db]++ } else { $counts[$db] = 1 }
    }
}
$reader.Close()

Write-Host ""
Write-Host "=== tables per database in dump ==="
$counts.GetEnumerator() | Sort-Object Name | ForEach-Object {
    "{0} : {1}" -f $_.Key, $_.Value
}
