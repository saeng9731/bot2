# -*- coding: utf-8 -*-
"""
min_craw_backfill.py - 분봉 1년치 백필 스크립트 (base_dt 걸어가기 방식)

- mock/실전 REST ka10080 에서 base_dt(기준일) 를 거슬러 올라가며 과거 분봉을 수집
- 기존 분봉 코드(get_total_data_min 등)는 수정하지 않음 (별도 스크립트)
- set_min_crawler_table 과 동일한 컬럼/이동평균/sum_volume 로 min_craw 에 저장
- 기존 테이블은 DROP 후 1년치 전체로 재생성

사용법:
    python min_craw_backfill.py                 # stock_item_all 전체 종목
    python min_craw_backfill.py 005930,000660   # 특정 종목만
    python min_craw_backfill.py --limit 5       # 앞 5종목만 (테스트)
"""
import sys, os, time, datetime, argparse
import requests
import pymysql
pymysql.install_as_MySQLdb()
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.types import Text, Integer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
from library import cf
from library.kiwoom_api import KiwoomRestClient

START_DT = '20250801'   # 1년 전 (API 제공 하한, 2025-08-01)
END_DT   = '20260814'   # 수집 끝 (마지막 거래일)

def get_stocks(only_codes, limit):
    eng = create_engine(
        f"mysql+pymysql://{cf.db_id}:{cf.db_passwd}@{cf.db_ip}:{cf.db_port}/daily_buy_list")
    rows = eng.execute("SELECT code, code_name FROM stock_item_all ORDER BY code").fetchall()
    if only_codes:
        rows = [r for r in rows if str(r[0]) in only_codes]
    if limit:
        rows = rows[:limit]
    return [(str(r[0]), str(r[1])) for r in rows]

def safe_int(v):
    s = str(v).strip()
    if not s or s in ('-', '+', 'None'):
        return 0
    try:
        return abs(int(float(s)))
    except (ValueError, TypeError):
        return 0

def fetch_batch(client, code, base_dt):
    """ka10080 1회 호출 -> 분봉 row 리스트 (파싱은 _parse_opt10080 과 동일)"""
    url = f'{client.base_url}/api/dostk/chart'
    headers = {
        'Content-Type': 'application/json;charset=UTF-8',
        'authorization': f'Bearer {client.access_token}',
        'api-id': 'ka10080', 'cont-yn': 'N', 'next-key': '',
    }
    body = {'stk_cd': code, 'tic_scope': '1', 'upd_stkpc_tp': '1', 'base_dt': base_dt}
    r = requests.post(url, headers=headers, json=body, timeout=30)
    if r.status_code != 200:
        print(f"    HTTP {r.status_code} - retry")
        time.sleep(2)
        return [], True
    data = r.json()
    rows = data.get('stk_min_pole_chart_qry', []) or data.get('stk_min_pole_qry', [])
    if isinstance(rows, dict):
        rows = [rows]
    out = []
    for row in rows:
        dt_val = str(row.get('cntr_tm', row.get('dt', '')))
        if not dt_val or len(dt_val) < 12:
            continue
        out.append({
            'date': dt_val[:12],
            'open': safe_int(row.get('open_pric', row.get('open_prc', 0))),
            'high': safe_int(row.get('high_pric', row.get('high_prc', 0))),
            'low': safe_int(row.get('low_pric', row.get('low_prc', 0))),
            'close': safe_int(row.get('cur_prc', 0)),
            'volume': safe_int(row.get('trde_qty', row.get('tr_vol', 0))),
        })
    cont = r.headers.get('cont-yn', 'N')
    return out, (cont == 'Y')


def backfill_stock(client, code, code_name):
    """한 종목 1년치 수집 + 가공 + 저장. 저장 행 수 반환"""
    all_rows = []
    base_dt = END_DT
    while base_dt >= START_DT:
        rows, _ = fetch_batch(client, code, base_dt)
        if not rows:
            break
        all_rows.extend(rows)
        earliest = min(r['date'][:8] for r in rows)
        if earliest <= START_DT:
            break
        d = datetime.datetime.strptime(earliest, '%Y%m%d') - datetime.timedelta(days=1)
        base_dt = d.strftime('%Y%m%d')
        time.sleep(1.0)  # rate limit (유량=1)

    if not all_rows:
        return 0

    df = pd.DataFrame(all_rows).drop_duplicates(subset='date')
    df = df.sort_values('date').reset_index(drop=True)

    # set_min_crawler_table 과 동일한 파생 컬럼 계산
    df['check_item'] = 0
    df['code'] = code
    df['code_name'] = code_name
    df['d1_diff_rate'] = round((df['close'] - df['close'].shift(1)) / df['close'].shift(1) * 100, 2)
    df['d1_diff_rate'] = df['d1_diff_rate'].replace([float('inf'), float('-inf')], 0)
    for n in (5, 10, 20, 40, 60, 80, 100, 120):
        clo = df['close'].rolling(window=n).mean()
        df[f'clo{n}'] = round(clo, 2)
        df[f'clo{n}_diff_rate'] = round((df['close'] - clo) / clo * 100, 2)
        df[f'yes_clo{n}'] = df[f'clo{n}'].shift(1)
        df[f'vol{n}'] = round(df['volume'].rolling(window=n).mean(), 2)

    # 정수 변환 (set_min_crawler_table line 493-503 동일)
    int_cols = ['close', 'open', 'high', 'low', 'volume', 'sum_volume',
                'clo5', 'clo10', 'clo20', 'clo40', 'clo60', 'clo80', 'clo100', 'clo120',
                'yes_clo5', 'yes_clo10', 'yes_clo20', 'yes_clo40', 'yes_clo60', 'yes_clo80',
                'yes_clo100', 'yes_clo120',
                'vol5', 'vol10', 'vol20', 'vol40', 'vol60', 'vol80', 'vol100', 'vol120']
    df['sum_volume'] = 0
    df[int_cols] = df[int_cols].fillna(0).astype(int)

    # sum_volume 누적 (set_min_crawler_table line 504-521 동일)
    temp_date = 0
    sum_volume = 0
    for i in range(0, len(df)):
        temp_index = len(df) - i - 1
        if (int(df.loc[temp_index, 'date']) - int(temp_date)) > 9000:
            sum_volume = 0
        temp_date = df.loc[temp_index, 'date']
        sum_volume += int(df.loc[temp_index, 'volume'])
        df.loc[temp_index, 'sum_volume'] = sum_volume

    cols = ['date', 'check_item', 'code', 'code_name', 'd1_diff_rate',
            'close', 'open', 'high', 'low', 'volume', 'sum_volume',
            'clo5', 'clo10', 'clo20', 'clo40', 'clo60', 'clo80', 'clo100', 'clo120',
            'clo5_diff_rate', 'clo10_diff_rate', 'clo20_diff_rate', 'clo40_diff_rate',
            'clo60_diff_rate', 'clo80_diff_rate', 'clo100_diff_rate', 'clo120_diff_rate',
            'yes_clo5', 'yes_clo10', 'yes_clo20', 'yes_clo40', 'yes_clo60', 'yes_clo80',
            'yes_clo100', 'yes_clo120',
            'vol5', 'vol10', 'vol20', 'vol40', 'vol60', 'vol80', 'vol100', 'vol120']
    df = df[cols]

    # 저장 (기존 테이블 DROP 후 재생성)
    eng = create_engine(
        f"mysql+pymysql://{cf.db_id}:{cf.db_passwd}@{cf.db_ip}:{cf.db_port}/min_craw")
    eng.execute(f"DROP TABLE IF EXISTS `{code_name}`")
    dtypes = dict(zip(cols, [Text] * len(cols)))
    for c in ['check_item', 'close', 'open', 'high', 'low', 'volume', 'sum_volume',
              'clo5', 'clo10', 'clo20', 'clo40', 'clo60', 'clo80', 'clo100', 'clo120',
              'yes_clo5', 'yes_clo10', 'yes_clo20', 'yes_clo40', 'yes_clo60', 'yes_clo80',
              'yes_clo100', 'yes_clo120',
              'vol5', 'vol10', 'vol20', 'vol40', 'vol60', 'vol80', 'vol100', 'vol120']:
        dtypes[c] = Integer
    df.to_sql(name=code_name, con=eng, if_exists='append', dtype=dtypes)
    try:
        idx = ''.join(c for c in code_name if c.isalnum())
        eng.execute(f"CREATE INDEX ix_{idx}_date ON `{code_name}` (date(12))")
    except Exception:
        pass
    return len(df)


def main():
    global END_DT, START_DT
    parser = argparse.ArgumentParser(description='분봉 1년치 백필')
    parser.add_argument('codes', nargs='?', default='', help='콤마 구분 종목코드 (없으면 전체)')
    parser.add_argument('--limit', type=int, default=0, help='처리 종목 수 제한 (테스트용)')
    parser.add_argument('--end', default=END_DT, help='수집 끝 날짜 YYYYMMDD')
    parser.add_argument('--start', default=START_DT, help='수집 시작 날짜 YYYYMMDD')
    args = parser.parse_args()

    END_DT = args.end
    START_DT = args.start

    only_codes = [c.strip() for c in args.codes.split(',') if c.strip()] if args.codes else None

    client = KiwoomRestClient()
    print(f"분봉 백필 시작: {START_DT} ~ {END_DT}, BASE={client.base_url}")

    stocks = get_stocks(only_codes, args.limit)
    print(f"대상 종목: {len(stocks)}개")

    done = 0
    total_rows = 0
    t_start = time.time()
    for i, (code, code_name) in enumerate(stocks, 1):
        t0 = time.time()
        try:
            n = backfill_stock(client, code, code_name)
            el = time.time() - t0
            print(f"[{i}/{len(stocks)}] {code} {code_name}: {n}행 ({el:.0f}초)")
            if n > 0:
                done += 1
                total_rows += n
        except Exception as e:
            print(f"[{i}/{len(stocks)}] {code} {code_name}: 오류 {e}")
        time.sleep(0.5)

    t_total = time.time() - t_start
    print(f"===== 완료: {done}개 종목, 총 {total_rows}행, 소요 {t_total/3600:.1f}시간 =====")

if __name__ == '__main__':
    main()

