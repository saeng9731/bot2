#!/bin/bash
# ============================================================
#  fetch_kind_from_github.sh
#  GitHub 저장소에 올라온 KIND 종목 리스트를 서버로 받아온다.
#  (서버 IP는 KIND 403이지만 GitHub은 접속 가능 → 이렇게 우회)
#
#  크론 등록 (UTC 06:30 = 한국 15:30, 콜렉터 15:35 직전):
#    # ① 먼저 GitHub Actions가 UTC 06:20(한국 15:20)에 KIND 파일을 갱신/커밋해야 합니다.
#    #    이 워크플로가 서버 fetch보다 나중에 돌면 항상 전날 파일을 받게 됩니다.
#    # ② 그 다음 서버가 아래 크론으로 내려받습니다.
#    30 6 * * 1-5 cd /home/opc/bot2 && bash sh/fetch_kind_from_github.sh >> /home/opc/bot2/log/fetch_kind.log 2>&1
# ============================================================

# ── 설정: GitHub 저장소 ──
REPO="saeng9731/bot2"

BASE="https://raw.githubusercontent.com/$REPO/main/KIND_xls"
cd /home/opc/bot2/KIND_xls || exit 1

FILES=(
  corpList_all.xls
  corpList_kospi.xls
  corpList_kosdaq.xls
  corpList_konex.xls
  corpList_managing.xls
  corpList_insincerity.xls
  invest_caution.xls
  invest_warning.xls
  invest_danger.xls
)

for f in "${FILES[@]}"; do
  if curl -sf -o "$f" "$BASE/$f"; then
    sz=$(stat -c%s "$f")
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $f OK ($sz bytes)"
  else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $f FAIL"
  fi
done
