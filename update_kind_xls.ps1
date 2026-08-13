# ============================================================
#  update_kind_xls.ps1
#  KIND 종목 리스트(엑셀 6종)를 로컬(집)에서 다운로드 후
#  오라클 서버로 업로드합니다. (KIND Akamai 403 우회용)
#
#  사용법: powershell -ExecutionPolicy Bypass -File update_kind_xls.ps1
#  실행 조건: 로컬(집)에서 실행해야 합니다 (서버 IP는 403)
# ============================================================

$SERVER_IP = "168.107.13.138"
$SSH_KEY   = "C:\Users\UserK\Desktop\opc3..4\ssh-key-2026-02-24.key"
$LOCAL_DIR = "C:\Users\UserK\Desktop\bot2\KIND_xls"

if (-not (Test-Path $LOCAL_DIR)) { New-Item -ItemType Directory -Path $LOCAL_DIR | Out-Null }

$ua   = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
$base = "http://kind.krx.co.kr/corpgeneral/corpList.do?method=download"

$items = @(
  @{ n = "corpList_all.xls";        u = "$base&searchType=13" },
  @{ n = "corpList_kospi.xls";      u = "$base&searchType=13&marketType=stockMkt" },
  @{ n = "corpList_kosdaq.xls";     u = "$base&searchType=13&marketType=kosdaqMkt" },
  @{ n = "corpList_konex.xls";      u = "$base&searchType=13&marketType=konexMkt" },
  @{ n = "corpList_managing.xls";   u = "$base&searchType=01" },
  @{ n = "corpList_insincerity.xls";u = "$base&searchType=05" }
)

Write-Host "=== KIND 종목 리스트 다운로드 (로컬) ==="
$ok = $true
foreach ($it in $items) {
    curl.exe -s -L -o "$LOCAL_DIR\$($it.n)" --max-time 30 -H "User-Agent: $ua" $it.u
    $sz = (Get-Item "$LOCAL_DIR\$($it.n)").Length
    Write-Host ("  {0,-28} {1,10:N0} bytes" -f $it.n, $sz)
    if ($sz -lt 1000) { $ok = $false; Write-Host "  [경고] 파일이 너무 작습니다 - 다운로드 실패?" -ForegroundColor Red }
}
if (-not $ok) { Write-Host "[중단] 다운로드 실패" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "=== 투자주의/경고/위험 종목 다운로드 (로컬, 최근 7일) ==="
$endD   = (Get-Date).ToString('yyyy-MM-dd')
$startD = (Get-Date).AddDays(-7).ToString('yyyy-MM-dd')
$warnCommon = "method=investattentwarnriskySub&searchCodeType=&searchCorpName=&repIsuSrtCd=&currentPageSize=3000&pageIndex=1&orderMode=3&orderStat=D&marketType=&searchFromDate=$endD"
$warnItems = @(
    @{ n = "invest_caution.xls";  d = "forward=invstcautnisu_down&menuIndex=1" },
    @{ n = "invest_warning.xls";  d = "forward=invstwarnisu_down&menuIndex=2" },
    @{ n = "invest_danger.xls";   d = "forward=invstriskisu_down&menuIndex=3" }
)
foreach ($it in $warnItems) {
    curl.exe -s -X POST "https://kind.krx.co.kr/investwarn/investattentwarnrisky.do" `
        -H "User-Agent: $ua" `
        -H "Referer: https://kind.krx.co.kr/investwarn/investattentwarnrisky.do" `
        --data "$warnCommon&$($it.d)&startDate=$startD&endDate=$endD" `
        -o "$LOCAL_DIR\$($it.n)" --max-time 30
    $sz = (Get-Item "$LOCAL_DIR\$($it.n)").Length
    Write-Host ("  {0,-28} {1,10:N0} bytes" -f $it.n, $sz)
    if ($sz -lt 100) { $ok = $false; Write-Host "  [경고] 파일이 너무 작습니다 - 다운로드 실패?" -ForegroundColor Red }
}
if (-not $ok) { Write-Host "[중단] 투자 종목 다운로드 실패" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "=== 서버 업로드 ($SERVER_IP) ==="
scp -i $SSH_KEY -o BatchMode=yes -o StrictHostKeyChecking=no `
    "$LOCAL_DIR\corpList_all.xls" `
    "$LOCAL_DIR\corpList_kospi.xls" `
    "$LOCAL_DIR\corpList_kosdaq.xls" `
    "$LOCAL_DIR\corpList_konex.xls" `
    "$LOCAL_DIR\corpList_managing.xls" `
    "$LOCAL_DIR\corpList_insincerity.xls" `
    "$LOCAL_DIR\invest_caution.xls" `
    "$LOCAL_DIR\invest_warning.xls" `
    "$LOCAL_DIR\invest_danger.xls" `
    "opc@${SERVER_IP}:/home/opc/bot2/KIND_xls/"
if ($LASTEXITCODE -ne 0) { Write-Host "[오류] 업로드 실패" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "=== 완료! 서버의 매일 콜렉터(KST 15:35)가 이 파일을 사용합니다 ==="
