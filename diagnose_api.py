# -*- coding: utf-8 -*-
"""
키움 REST API ka10081 (주식일봉차트) 응답 확인 스크립트 v2
- body를 직접 전송 (INPUT 래핑 없이) - 사용자 제공 fn_ka10081 방식
실행: python diagnose_api.py
"""
import json
import requests

from library.kiwoom_api import KiwoomRestClient, cf

def main():
    print("=== 키움 REST API ka10081 (주식일봉차트) 응답 확인 v2 ===")
    print(f"mock: {cf.kiwoom_is_mock}, base_url: {cf.kiwoom_api_base_url}")

    client = KiwoomRestClient()
    print(f"client.base_url: {client.base_url}")
    print(f"access_token: {client.access_token[:20]}...")
    print()

    # ka10081 주식일봉차트조회 (fn_ka10081 방식 그대로)
    url = f'{client.base_url}/api/dostk/chart'
    headers = {
        'Content-Type': 'application/json;charset=UTF-8',
        'authorization': f'Bearer {client.access_token}',
        'cont-yn': 'F',
        'next-key': '',
        'api-id': 'ka10081',
    }
    # 사용자 제공 예제와 동일 - body를 직접 전달 (INPUT 래핑 없음)
    body = {
        'stk_cd': '005930',      # 삼성전자
        'base_dt': '20260804',   # 기준일자
        'upd_stkpc_tp': '1',     # 수정주가구분
    }

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=15)
        data = resp.json()

        print(f"HTTP {resp.status_code}")
        print(f"응답 키 목록: {list(data.keys())}")
        print(f"return_msg: {data.get('return_msg', 'N/A')}")
        print()

        # 응답 저장
        with open('api_response_ka10081.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 데이터 상세 확인
        found = False
        for key in ['stk_dt_pole_qry', 'output', 'data', 'output1', 'stk_bsic_info_qry']:
            if key in data:
                out = data[key]
                print(f"[{key}] 데이터 수: {len(out) if isinstance(out, list) else type(out).__name__}")
                if isinstance(out, list) and len(out) > 0:
                    print(f"첫 row: {json.dumps(out[0], ensure_ascii=False)[:500]}")
                elif isinstance(out, dict):
                    print(f"값: {json.dumps(out, ensure_ascii=False)[:500]}")
                found = True
                break

        if not found and 'return_msg' not in data:
            print(f"전체 응답: {json.dumps(data, ensure_ascii=False)[:1500]}")

        if 'return_msg' not in data:
            print("\n★ 성공! api_response_ka10081.json 저장됨")
        elif '정상적으로 처리되었습니다' in str(data.get('return_msg', '')):
            print("\n★ 성공! return_msg = 정상적으로 처리되었습니다")
            # 전체 응답 재출력
            print(f"전체 응답: {json.dumps(data, ensure_ascii=False)[:2000]}")

    except Exception as e:
        print(f"에러: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()