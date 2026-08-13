# -*- coding: utf-8 -*-
"""
KIND 종목 리스트 엑셀을 다운로드해서 KIND_xls/ 폴더에 저장한다.
GitHub Actions에서 실행되어 저장소에 커밋/푸시되는 것을 전제로 한다.
"""
import os
import sys
import datetime
import urllib.request
import urllib.parse

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'KIND_xls')
os.makedirs(OUT_DIR, exist_ok=True)


def save(url, fname, data=None, referer=None):
    headers = {"User-Agent": UA}
    if referer:
        headers["Referer"] = referer
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(url, headers=headers, data=body)
    with urllib.request.urlopen(req, timeout=30) as r:
        content = r.read()
    path = os.path.join(OUT_DIR, fname)
    with open(path, 'wb') as f:
        f.write(content)
    print(f"{fname}: {len(content)} bytes")
    return len(content)


def main():
    ok = True
    base = 'https://kind.krx.co.kr/corpgeneral/corpList.do?method=download'

    # 1) 종목 리스트 6종 (GET)
    get_items = [
        ('corpList_all.xls',        f'{base}&searchType=13'),
        ('corpList_kospi.xls',      f'{base}&searchType=13&marketType=stockMkt'),
        ('corpList_kosdaq.xls',     f'{base}&searchType=13&marketType=kosdaqMkt'),
        ('corpList_konex.xls',      f'{base}&searchType=13&marketType=konexMkt'),
        ('corpList_managing.xls',   f'{base}&searchType=01'),
        ('corpList_insincerity.xls', f'{base}&searchType=05'),
    ]
    for fname, url in get_items:
        try:
            sz = save(url, fname)
            if sz < 1000:
                print(f"[경고] {fname} 크기 이상 ({sz})"); ok = False
        except Exception as e:
            print(f"[실패] {fname}: {e}"); ok = False

    # 2) 투자주의/경고/위험 종목 3종 (POST, 최근 7일)
    end_d = datetime.date.today().strftime('%Y-%m-%d')
    start_d = (datetime.date.today() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
    warn_url = 'https://kind.krx.co.kr/investwarn/investattentwarnrisky.do'
    warn_ref = 'https://kind.krx.co.kr/investwarn/investattentwarnrisky.do'
    common = {
        'method': 'investattentwarnriskySub',
        'searchCodeType': '', 'searchCorpName': '', 'repIsuSrtCd': '',
        'currentPageSize': '3000', 'pageIndex': '1', 'orderMode': '3', 'orderStat': 'D',
        'marketType': '', 'searchFromDate': end_d,
        'startDate': start_d, 'endDate': end_d,
    }
    warn_items = [
        ('invest_caution.xls', 'invstcautnisu_down', '1'),
        ('invest_warning.xls', 'invstwarnisu_down', '2'),
        ('invest_danger.xls',  'invstriskisu_down', '3'),
    ]
    for fname, fwd, menu in warn_items:
        data = dict(common, forward=fwd, menuIndex=menu)
        try:
            sz = save(warn_url, fname, data=data, referer=warn_ref)
            if sz < 100:
                print(f"[경고] {fname} 크기 이상 ({sz})"); ok = False
        except Exception as e:
            print(f"[실패] {fname}: {e}"); ok = False

    print("=== 다운로드 완료 ===")
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
