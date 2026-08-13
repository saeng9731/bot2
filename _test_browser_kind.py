# -*- coding: utf-8 -*-
# 서버에서 실제 브라우저(playwright chromium)로 KIND 접속 테스트
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        locale="ko-KR"
    )
    page = ctx.new_page()
    try:
        resp = page.goto(
            "https://kind.krx.co.kr/investwarn/investattentwarnrisky.do?method=investattentwarnriskyMain",
            timeout=30000, wait_until="domcontentloaded")
        print("KIND 접속 상태:", resp.status)
        print("페이지 제목:", page.title())
        # 상장법인목록 페이지도 테스트
        resp2 = page.goto(
            "https://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13",
            timeout=30000, wait_until="domcontentloaded")
        print("상장법인목록 상태:", resp2.status)
    except Exception as e:
        print("접속 실패:", e)
    browser.close()
print("=== 테스트 완료 ===")
