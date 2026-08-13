# -*- coding: utf-8 -*-
"""
fetch_kind_from_github.py
GitHub 저장소에 올라온 KIND 종목 리스트 파일을 서버로 자동 내려받는다.
(서버 IP는 KIND 403이지만 GitHub 접속은 정상 → 이 방식으로 우회)

사용법:
    python fetch_kind_from_github.py

크론 등록 (UTC 06:30 = 한국 15:30, 서버 콜렉터 15:35 직전):
    30 6 * * 1-5 cd /home/opc/bot2 && python fetch_kind_from_github.py >> log/fetch_kind.log 2>&1
"""
import os
import sys
import datetime
import urllib.request

# ═══════════════════════════════════════════════════════════
# 설정 (여기만 수정하면 됩니다)
REPO   = "saeng9731/bot2"   # ← GitHub 저장소
BRANCH = "main"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'KIND_xls')
# ═══════════════════════════════════════════════════════════

FILES = [
    "corpList_all.xls",
    "corpList_kospi.xls",
    "corpList_kosdaq.xls",
    "corpList_konex.xls",
    "corpList_managing.xls",
    "corpList_insincerity.xls",
    "invest_caution.xls",
    "invest_warning.xls",
    "invest_danger.xls",
]

# 파일별 최소 크기(byte) - 다운로드 실패/빈 파일 감지용
MIN_SIZE = {
    "corpList_all.xls":         50000,
    "corpList_kospi.xls":       10000,
    "corpList_kosdaq.xls":      10000,
    "corpList_konex.xls":        1000,
    "corpList_managing.xls":     1000,
    "corpList_insincerity.xls":   100,
    "invest_caution.xls":        1000,
    "invest_warning.xls":         100,
    "invest_danger.xls":          100,
}


def now_str():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def main():
    if REPO == "USERNAME/REPO":
        print(f"[{now_str()}] [오류] REPO 를 실제 GitHub 저장소로 수정하세요. (예: '내계정/bot2')")
        sys.exit(1)

    os.makedirs(OUT_DIR, exist_ok=True)
    ok = True

    print(f"[{now_str()}] GitHub에서 KIND 파일 내려받기 시작 (저장소: {REPO})")
    for fname in FILES:
        url = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/KIND_xls/{fname}"
        dest = os.path.join(OUT_DIR, fname)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            with open(dest, 'wb') as fp:
                fp.write(data)

            min_sz = MIN_SIZE.get(fname, 0)
            if len(data) < min_sz:
                print(f"[{now_str()}] {fname} [경고] 크기 이상 ({len(data)} bytes / 최소 {min_sz})")
                ok = False
            else:
                print(f"[{now_str()}] {fname} OK ({len(data)} bytes)")
        except Exception as e:
            print(f"[{now_str()}] {fname} FAIL - {e}")
            ok = False

    if ok:
        print(f"[{now_str()}] === 모두 정상 내려받음 (KIND_xls/ {len(FILES)}개) ===")
    else:
        print(f"[{now_str()}] === 일부 파일 실패 (위 로그 확인) ===")
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
