ver = "#version 1.0.0 (REST API)"
print(f"kiwoom_api Version: {ver}")

"""
키움증권 REST API 기반 모듈 (오라클 클라우드 / Linux 호환)
기존 library/open_api.py (QAxWidget 기반) 와 동일한 인터페이스를 제공하되,
HTTP REST API 를 사용하여 Windows COM 없이도 동작하도록 구현.
"""

import datetime
import sys
import time
import json
import re
import os
from collections import defaultdict

import requests
import pandas as pd
import numpy as np
import pymysql
from pandas import DataFrame
from sqlalchemy import create_engine, event, Text, Float
from sqlalchemy.pool import Pool

from library.simulator_func_mysql import *
from library import cf
from library.logging_pack import logger

import warnings
warnings.simplefilter(action='ignore', category=UserWarning)

pymysql.install_as_MySQLdb()

TR_REQ_TIME_INTERVAL = 0.3
code_pattern = re.compile(r'\d{6}')


# ──────────────────────────────────────────────
#  ka10001(주식기본정보) REST 응답 영문 키 → OCX 한글 키 변환
#  (실제 응답 키는 실행 로그의 'ka10001 응답 키 목록'으로 확인 후 필요시 추가)
# ──────────────────────────────────────────────
REST_FINANCE_KEY_MAP = {
    # ka10001 실제 응답 키 기준 (mockapi.kiwoom.com 2026-08-06 확인)
    'stk_cd': '종목코드',
    'stk_nm': '종목명',
    'setl_mm': '결산월',
    'fav': '액면가',
    'cap': '자본금',
    'flo_stk': '상장주식',
    'crd_rt': '신용비율',
    'oyr_hgst': '연중최고',
    'oyr_lwst': '연중최저',
    'mac': '시가총액',
    'roe': 'ROE',
    'eps': 'EPS',
    'for_exh_rt': '외인소진률',
    'repl_pric': '대용가',
    'per': 'PER',
    'pbr': 'PBR',
    'ev': 'EV',
    'bps': 'BPS',
    'sale_amt': '매출액',
    'bus_pro': '영업이익',
    'cup_nga': '당기순이익',
    '250hgst': '250최고',
    '250lwst': '250최저',
    'upl_pric': '상한가',
    'lst_pric': '하한가',
    'base_pric': '기준가',
    '250hgst_pric_dt': '250최고가일',
    '250lwst_pric_dt': '250최저가일',
    '250lwst_pric_pre_rt': '250최저가대비율',
    'trde_pre': '거래대비',
    'dstr_stk': '유통주식',
    'dstr_rt': '유통비율',
}



# ────────────────────────────────────────────────────────────
#  SQL 보조 함수 (open_api.py 와 동일)
# ────────────────────────────────────────────────────────────
def escape_percentage(conn, clauseelement, multiparams, params):
    if isinstance(clauseelement, str) and '%' in clauseelement and multiparams is not None:
        while True:
            replaced = re.sub(r'([^%])%([^%s])', r'\1%%\2', clauseelement)
            if replaced == clauseelement:
                break
            clauseelement = replaced
    return clauseelement, multiparams, params


def setup_sql_mod(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("SET sql_mode = ''")


event.listen(Pool, 'connect', setup_sql_mod)
event.listen(Pool, 'first_connect', setup_sql_mod)


class RateLimitExceeded(Exception):
    pass


def timedout_exit(widget):
    logger.debug("서버로 부터 응답이 없어 프로그램을 종료합니다.")
    time.sleep(3)
    sys.exit(-1)


# ────────────────────────────────────────────────────────────
#  키움 REST API 클라이언트
# ────────────────────────────────────────────────────────────
class KiwoomRestClient:
    """키움증권 REST API HTTP 클라이언트"""

    def __init__(self):
        self.base_url = cf.kiwoom_api_base_url
        # 모의투자 여부에 따라 URL 분기
        if cf.kiwoom_is_mock:
            self.base_url = 'https://mockapi.kiwoom.com'
        else:
            self.base_url = 'https://api.kiwoom.com'

        self.api_key = cf.kiwoom_api_key
        self.api_secret = cf.kiwoom_api_secret
        self.access_token = cf.kiwoom_access_token or ''
        self.token_expire_time = None

        # 토큰이 없으면 자동 발급
        if not self.access_token and self.api_key and self.api_secret:
            self.issue_token()

    def issue_token(self):
        """OAuth2 access_token 발급 (키움증권 공식 예제 기반)"""
        url = f'{self.base_url}/oauth2/token'
        headers = {
            'Content-Type': 'application/json;charset=UTF-8',  # 컨텐츠타입
        }
        body = {
            'grant_type': 'client_credentials',  # grant_type
            'appkey': self.api_key,  # 앱키
            'secretkey': self.api_secret  # 시크릿키
        }
        try:
            resp = requests.post(url, headers=headers, json=body, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            # 응답에서 access_token 추출 (키움 REST API 응답 키: access_token 또는 token)
            self.access_token = data.get('access_token', data.get('token', ''))
            if not self.access_token:
                logger.critical(f"REST API 토큰 발급 응답에 access_token이 없습니다: {data}")
                raise ValueError("access_token not found in response")
            # 토큰 만료 시간 설정 (기본 6시간)
            expires_in = int(data.get('expires_in', 21600))
            self.token_expire_time = datetime.datetime.now() + datetime.timedelta(seconds=expires_in - 300)
            logger.debug("REST API 토큰 발급 완료")
        except Exception as e:
            logger.critical(f"REST API 토큰 발급 실패: {e}")
            raise

    def _check_token(self):
        """토큰 만료 체크 후 갱신"""
        if self.token_expire_time and datetime.datetime.now() >= self.token_expire_time:
            self.issue_token()

    def request(self, api_id, params=None, cont_yn='F', next_key=''):
        """
        TR 조회 요청 (키움 REST API)
        api_id: TR 코드 (예: opw00001, opt10081)
        params: 입력값 딕셔너리 (한글 키 사용)
        cont_yn: 연속조회 여부 ('F'=첫 조회, 'T'=연속 조회)
        next_key: 연속조회 키 (첫 조회 시 '')

        endpoint 분기:
          - 계좌/주문 관련 TR (opw00001, opw00018, opt10073, opt10074 등): /api/dostk/acnt
          - 일반 조회 TR (opt10081, opt10001 등): /api/dostk
        """
        self._check_token()
        # 계좌 관련 TR은 /api/dostk/acnt 사용
        account_tr_codes = (
            'opw00001', 'opw00018', 'opw00015', 'opw00004', 'opw00005',
            'opt10073', 'opt10074', 'opt10076', 'opt10075',
            'opw00002', 'opw00003', 'opw00007', 'opw00012',
        )
        if api_id in account_tr_codes:
            endpoint = '/api/dostk/acnt'
        elif api_id in ('opt10081', 'opt10080', 'ka10081', 'ka10080'):  # 차트 조회
            endpoint = '/api/dostk/chart'
        elif api_id in ('opt10001', 'ka10001'):  # 주식기본정보
            endpoint = '/api/dostk/stkinfo'
        else:
            endpoint = '/api/dostk'

        url = f'{self.base_url}{endpoint}'
        headers = {
            'Content-Type': 'application/json;charset=UTF-8',
            'authorization': f'Bearer {self.access_token}',
            'api-id': api_id,
            'cont-yn': cont_yn,          # 연속조회 여부 ('F' 첫조회 / 'T' 연속조회)
            'next-key': next_key,        # 연속조회 키
        }
        body = params or {}
        # (2026-08-05 수정) 키움 REST API는 ka10001/ka10081/ka10080 등은 body를 직접 전달해야 함
        # 기존 {"INPUT": {...}} 래핑은 stk_cd 등 필수 파라미터가 누락되는 원인이었음
        # 계좌 관련 API는 별도 처리 필요하지만, 여기서는 body를 그대로 전달

        try:
            resp = requests.post(url, headers=headers, json=body, timeout=30)
            # 성공 여부와 무관하게 응답 본문 먼저 파싱 (키움 오류코드 확인용)
            try:
                resp_data = resp.json()
            except ValueError:
                resp_data = {}

            # HTTP 오류 발생 시 키움 오류코드 추출
            if resp.status_code != 200:
                err_code = resp_data.get('code', resp_data.get('errorCode', '?'))
                err_msg = resp_data.get('msg1', resp_data.get('message', resp.text[:200]))
                logger.critical(f"REST API 요청 실패 [{api_id}]: HTTP {resp.status_code}, 오류코드={err_code}, 사유={err_msg}")
                if resp.status_code == 429:
                    raise RateLimitExceeded('요청제한 횟수를 초과하였습니다.')
                raise Exception(f"Kiwoom API error [{api_id}]: code={err_code}, msg={err_msg}")

            # 연속조회 정보를 응답 본문에 병합 (다음 요청 시 필요)
            # ka10081/ka10080 차트 API는 응답 헤더의 cont-yn / next-key 로 연속조회 여부를 알려줌
            resp_data['_cont_yn'] = resp.headers.get('cont-yn', 'F')
            resp_data['_next_key'] = resp.headers.get('next-key', '')

            # (2026-08-09 수정) 일부 API는 연속조회 정보를 헤더가 아닌 body로 반환하므로 보완
            # 헤더에 없으면 body에서 cont_yn / next_key 를 찾는다 (중복 수신 방지 핵심)
            if not resp_data['_cont_yn'] or resp_data['_cont_yn'] == 'F':
                resp_data['_cont_yn'] = resp_data.get(
                    'cont_yn', resp_data.get('contYn',
                    resp_data.get('cont-yn', resp_data.get('cont', 'F'))))
            if not resp_data['_next_key']:
                resp_data['_next_key'] = resp_data.get(
                    'next_key', resp_data.get('nextKey',
                    resp_data.get('next-key', '')))

            return resp_data
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 429:
                raise RateLimitExceeded('요청제한 횟수를 초과하였습니다.')
            logger.critical(f"REST API 요청 실패 [{api_id}]: {e}")
            raise
        except Exception as e:
            logger.critical(f"REST API 요청 실패 [{api_id}]: {e}")
            raise

    def request_order(self, api_id, params=None):
        """주문 요청 (POST /api/dostkord)"""
        self._check_token()
        url = f'{self.base_url}/api/dostkord'
        headers = {
            'Content-Type': 'application/json;charset=UTF-8',
            'authorization': f'Bearer {self.access_token}',
            'api-id': api_id,
        }
        body = params or {}

        try:
            resp = requests.post(url, headers=headers, json=body, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            if resp.status_code == 429:
                raise RateLimitExceeded('요청제한 횟수를 초과하였습니다.')
            logger.critical(f"REST API 주문 실패 [{api_id}]: {e}")
            raise
        except Exception as e:
            logger.critical(f"REST API 주문 실패 [{api_id}]: {e}")
            raise


# ────────────────────────────────────────────────────────────
#  open_api 호환 클래스 (REST API 기반)
# ────────────────────────────────────────────────────────────
class open_api:
    """
    기존 library/open_api.py 의 open_api(QAxWidget) 클래스와
    동일한 인터페이스를 제공하는 REST API 기반 클래스.
    QAxWidget 을 상속하지 않으므로 Linux 에서도 동작.
    """

    def __init__(self):
        # openapi 호출 횟수를 저장하는 변수
        self.rq_count = 0
        self.date_setting()
        self.tr_loop_count = 0
        self.call_time = datetime.datetime.now()

        # REST API 클라이언트 초기화
        self.rest_client = KiwoomRestClient()

        # openapi연동 (REST API는 별도 연결 없음, 토큰만 확인)
        self.comm_connect()

        # 계좌 정보 가져오는 함수
        self.account_info()
        self.variable_setting()

        # simulator_func_mysql 클래스 호출
        self.sf = simulator_func_mysql(self.simul_num, 'real', self.db_name)
        logger.debug("self.sf.simul_num(알고리즘 번호) : %s", self.sf.simul_num)
        logger.debug("self.sf.db_to_realtime_daily_buy_list_num : %s", self.sf.db_to_realtime_daily_buy_list_num)
        logger.debug("self.sf.sell_list_num : %s", self.sf.sell_list_num)

        # setting_data 테이블이 존재하지 않으면 구축
        if not self.sf.is_simul_table_exist(self.db_name, "setting_data"):
            self.init_db_setting_data()
        else:
            logger.debug("setting_data db 존재한다!!!")

        # invest_unit 설정
        self.sf_variable_setting()
        self.ohlcv = defaultdict(list)
        self._data = {}
        self.remained_data = False

    # ──────────────────────────────────────────────
    #  날짜 세팅
    # ──────────────────────────────────────────────
    def date_setting(self):
        self.today = datetime.datetime.today().strftime("%Y%m%d")
        self.today_detail = datetime.datetime.today().strftime("%Y%m%d%H%M")

    # ──────────────────────────────────────────────
    #  invest_unit 가져오기
    # ──────────────────────────────────────────────
    def get_invest_unit(self):
        logger.debug("get_invest_unit 함수에 들어왔습니다!")
        sql = "select invest_unit from setting_data limit 1"
        return self.engine_JB.execute(sql).fetchall()[0][0]

    # ──────────────────────────────────────────────
    #  simulator_func_mysql 설정값 가져오기
    # ──────────────────────────────────────────────
    def sf_variable_setting(self):
        self.date_rows_yesterday = self.sf.get_recent_daily_buy_list_date()

        if not self.sf.is_simul_table_exist(self.db_name, "all_item_db"):
            logger.debug("all_item_db 없어서 생성!! init !! ")
            self.invest_unit = 0
            self.db_to_all_item(0, 0, 0, 0, 0)
            self.delete_all_item("0")

        if not self.check_set_invest_unit():
            self.set_invest_unit()
        else:
            self.invest_unit = self.get_invest_unit()
            self.sf.invest_unit = self.invest_unit

    # ──────────────────────────────────────────────
    #  보유량 가져오기
    # ──────────────────────────────────────────────
    def get_holding_amount(self, code):
        logger.debug("get_holding_amount 함수에 들어왔습니다!")
        sql = "select holding_amount from possessed_item where code = '%s' group by code"
        rows = self.engine_JB.execute(sql % (code)).fetchall()
        if len(rows):
            return rows[0][0]
        else:
            logger.debug("get_holding_amount 비어있다 !")
            return False

    # ──────────────────────────────────────────────
    #  setting_data invest_unit 확인
    # ──────────────────────────────────────────────
    def check_set_invest_unit(self):
        sql = "select invest_unit, set_invest_unit from setting_data limit 1"
        rows = self.engine_JB.execute(sql).fetchall()
        if rows[0][1] == self.today:
            self.invest_unit = rows[0][0]
            return True
        else:
            return False

    # ──────────────────────────────────────────────
    #  매수 금액 설정
    # ──────────────────────────────────────────────
    def set_invest_unit(self):
        self.get_d2_deposit()
        self.check_balance()
        # total_purchase_price가 없으면 0으로 처리 (REST API 응답에 따라)
        total_purchase = getattr(self, 'total_purchase_price', 0) or 0
        self.total_invest = self.change_format(
            str(int(self.d2_deposit_before_format or 0) + int(total_purchase)))
        self.invest_unit = self.sf.invest_unit
        sql = "UPDATE setting_data SET invest_unit='%s',set_invest_unit='%s' limit 1"
        self.engine_JB.execute(sql % (self.invest_unit, self.today))

    # ──────────────────────────────────────────────
    #  변수 설정
    # ──────────────────────────────────────────────
    def variable_setting(self):
        logger.debug("variable_setting 함수에 들어왔다.")
        self.get_today_buy_list_code = 0
        self.cf = cf
        self.reset_opw00018_output()
        if self.account_number == cf.real_account:
            self.simul_num = cf.real_simul_num
            logger.debug("실전!@@@@@@@@@@@" + cf.real_account)
            self.db_name_setting(cf.real_db_name)
            self.mod_gubun = 100
        elif self.account_number == cf.imi1_accout:
            logger.debug("모의투자 1!!")
            self.simul_num = cf.imi1_simul_num
            self.db_name_setting(cf.imi1_db_name)
            self.mod_gubun = 1
        else:
            logger.debug("계정이 존재하지 않습니다!! library/cf.py 파일에 계좌번호를 입력해주세요!")
            exit(1)
        self.jango_is_null = True
        self.py_gubun = False

    # ──────────────────────────────────────────────
    #  DB 관련 함수들 (open_api.py 와 동일)
    # ──────────────────────────────────────────────
    def create_database(self, cursor):
        logger.debug("create_database!!! {}".format(self.db_name))
        sql = 'CREATE DATABASE {}'
        cursor.execute(sql.format(self.db_name))

    def is_database_exist(self, cursor):
        sql = "SELECT 1 FROM Information_schema.SCHEMATA WHERE SCHEMA_NAME = '{}'"
        if cursor.execute(sql.format(self.db_name)):
            logger.debug("%s 데이터 베이스가 존재한다! ", self.db_name)
            return True
        else:
            logger.debug("%s 데이터 베이스가 존재하지 않는다! ", self.db_name)
            return False

    def db_name_setting(self, db_name):
        self.db_name = db_name
        logger.debug("db name !!! : %s", self.db_name)
        conn = pymysql.connect(
            host=cf.db_ip,
            port=int(cf.db_port),
            user=cf.db_id,
            password=cf.db_passwd,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        with conn.cursor() as cursor:
            if not self.is_database_exist(cursor):
                self.create_database(cursor)
            self.engine_JB = create_engine(
                "mysql+mysqldb://" + cf.db_id + ":" + cf.db_passwd + "@" + cf.db_ip + ":" + cf.db_port + "/" + db_name,
                encoding='utf-8'
            )
            self.basic_db_check(cursor)
        conn.commit()
        conn.close()

        self.engine_craw = create_engine(
            "mysql+mysqldb://" + cf.db_id + ":" + cf.db_passwd + "@" + cf.db_ip + ":" + cf.db_port + "/min_craw",
            encoding='utf-8')
        self.engine_daily_craw = create_engine(
            "mysql+mysqldb://" + cf.db_id + ":" + cf.db_passwd + "@" + cf.db_ip + ":" + cf.db_port + "/daily_craw",
            encoding='utf-8')
        self.engine_daily_buy_list = create_engine(
            "mysql+mysqldb://" + cf.db_id + ":" + cf.db_passwd + "@" + cf.db_ip + ":" + cf.db_port + "/daily_buy_list",
            encoding='utf-8')

        event.listen(self.engine_craw, 'before_execute', escape_percentage, retval=True)
        event.listen(self.engine_daily_craw, 'before_execute', escape_percentage, retval=True)
        event.listen(self.engine_daily_buy_list, 'before_execute', escape_percentage, retval=True)

    # ──────────────────────────────────────────────
    #  계좌 정보
    # ──────────────────────────────────────────────
    def account_info(self):
        logger.debug("account_info 함수에 들어왔습니다!")
        # REST API에서는 cf.py의 계좌번호를 사용
        if cf.kiwoom_is_mock:
            self.account_number = cf.imi1_accout
        else:
            self.account_number = cf.real_account
        logger.debug("계좌번호 : " + self.account_number)

    # ──────────────────────────────────────────────
    #  로그인 정보 (REST API 버전)
    # ──────────────────────────────────────────────
    def get_login_info(self, tag):
        logger.debug("get_login_info 함수에 들어왔습니다!")
        try:
            if tag == "ACCNO":
                if cf.kiwoom_is_mock:
                    return cf.imi1_accout + ';'
                else:
                    return cf.real_account + ';'
            elif tag == "USER_ID":
                return ''
            elif tag == "USER_NAME":
                return 'REST_API_USER'
            elif tag == "GetServerGubun":
                return '1' if cf.kiwoom_is_mock else '0'
            else:
                return ''
        except Exception as e:
            logger.critical(e)

    # ──────────────────────────────────────────────
    #  REST API 연결 (토큰 확인)
    # ──────────────────────────────────────────────
    def comm_connect(self):
        logger.debug("REST API 연결 (토큰 확인)")
        # REST API는 별도 연결 불필요, 토큰만 유효하면 됨
        if not self.rest_client.access_token:
            logger.critical("REST API 토큰이 없습니다. cf.py의 KIWOOM_API_KEY, KIWOOM_API_SECRET를 설정해주세요.")
            if not cf.kiwoom_api_key or not cf.kiwoom_api_secret:
                logger.critical("KIWOOM_API_KEY 또는 KIWOOM_API_SECRET이 설정되지 않았습니다.")
                logger.critical("환경변수 KIWOOM_API_KEY, KIWOOM_API_SECRET를 설정하거나 cf.py에 직접 입력해주세요.")
                exit(1)
        logger.debug("REST API connected")

    def _event_connect(self, err_code):
        pass

    def _receive_msg(self, sScrNo, sRQName, sTrCode, sMsg):
        logger.debug(sMsg)

    # ──────────────────────────────────────────────
    #  dynamicCall (REST API 매핑)
    # ──────────────────────────────────────────────
    def dynamicCall(self, method, *args):
        """
        기존 QAxWidget.dynamicCall 을 REST API 호출로 매핑.
        """
        method = method.strip()

        # GetCodeListByMarket(QString) - 시장별 종목코드
        if method.startswith('GetCodeListByMarket'):
            market = args[0] if args else '0'
            return self._get_code_list_by_market_rest(market)

        # GetMasterCodeName(QString) - 종목명
        elif method.startswith('GetMasterCodeName'):
            code = args[0] if args else ''
            return self._get_master_code_name_rest(code)

        # GetMasterListedStockCnt(QString) - 상장주식수
        elif method.startswith('GetMasterListedStockCnt'):
            code = args[0] if args else ''
            return self._get_master_listed_stock_cnt_rest(code)

        # GetMasterConstruction(QString) - 감리구분
        elif method.startswith('GetMasterConstruction'):
            code = args[0] if args else ''
            return self._get_master_construction_rest(code)

        # GetMasterStockState(QString) - 증거금비율, 거래정지여부 등
        elif method.startswith('GetMasterStockState'):
            code = args[0] if args else ''
            return self._get_master_stock_state_rest(code)

        # GetThemeGroupList(int) - 테마그룹 리스트
        elif method.startswith('GetThemeGroupList'):
            return self._get_theme_group_list_rest()

        # GetThemeGroupCode(QString) - 테마그룹 종목코드
        elif method.startswith('GetThemeGroupCode'):
            theme_code = args[0] if args else ''
            return self._get_theme_group_code_rest(theme_code)

        # GetMasterStockInfo(QString) - 주식종목 정보
        elif method.startswith('GetMasterStockInfo'):
            code = args[0] if args else ''
            return self._get_master_stock_info_rest(code)

        # KOA_Functions - 특수함수
        elif method.startswith('KOA_Functions'):
            func_name = args[0] if args else ''
            code = args[1] if len(args) > 1 else ''
            return self._koa_functions_rest(func_name, code)

        # CommConnect()
        elif method.startswith('CommConnect'):
            self.comm_connect()
            return 0

        # GetLoginInfo(QString)
        elif method.startswith('GetLoginInfo'):
            tag = args[0] if args else ''
            return self.get_login_info(tag)

        # SetInputValue(QString, QString)
        elif method.startswith('SetInputValue'):
            # 입력값은 self._input_values 에 저장
            if not hasattr(self, '_input_values'):
                self._input_values = {}
            self._input_values[args[0]] = args[1]
            return 0

        # CommRqData(QString, QString, int, QString)
        elif method.startswith('CommRqData'):
            rqname = args[0]
            trcode = args[1]
            next_flag = args[2]
            screen_no = args[3]
            return self._comm_rq_data_rest(rqname, trcode, next_flag, screen_no)

        # GetCommData(QString, QString, int, QString)
        elif method.startswith('GetCommData'):
            trcode = args[0]
            rqname = args[1]
            index = args[2]
            item_name = args[3]
            return self._get_comm_data_rest(trcode, rqname, index, item_name)

        # GetRepeatCnt(QString, QString)
        elif method.startswith('GetRepeatCnt'):
            trcode = args[0]
            rqname = args[1]
            return self._get_repeat_cnt_rest(trcode, rqname)

        # SendOrder(...)
        elif method.startswith('SendOrder'):
            return self._send_order_rest(*args)

        # GetChejanData(int)
        elif method.startswith('GetChejanData'):
            fid = args[0] if args else 0
            return self._get_chejan_data_rest(fid)

        # GetConnectState()
        elif method.startswith('GetConnectState'):
            return 1  # REST API는 항상 연결됨

        else:
            logger.debug(f"dynamicCall: 지원하지 않는 메서드 - {method}")
            return ''

    # ──────────────────────────────────────────────
    #  REST API 기반 TR 데이터 처리
    # ──────────────────────────────────────────────
    def _comm_rq_data_rest(self, rqname, trcode, next_flag, screen_no):
        """
        REST API를 통한 TR 데이터 요청.
        기존 CommRqData 는 비동기 이벤트 방식이었으나,
        REST API는 동기식으로 응답을 받아 self._tr_response 에 저장.
        """
        self.exit_check()
        self.rq_count += 1
        self.call_time = datetime.datetime.now()

        # 입력값 준비 (키움 REST API는 한글 키를 그대로 사용: {"INPUT": {"계좌번호": "...", "비밀번호": "..."}})
        params = {}
        if hasattr(self, '_input_values'):
            params = dict(self._input_values)

        # OCX TR 코드 → REST API ID 변환
        tr_to_api = {
            'opt10081': 'ka10081',  # 주식일봉차트
            'opt10080': 'ka10080',  # 주식분봉차트
            'opt10001': 'ka10001',  # 주식기본정보
        }
        api_id = tr_to_api.get(trcode, trcode)

        try:
            # 한글 입력 키를 REST API 파라미터 키로 변환
            rest_params = self._tr_input_map(api_id, params)

            # 연속조회 여부 (next_flag == 2 이면 연속조회)
            # 이전 응답에서 저장해둔 next_key 사용
            cont_yn = 'T' if next_flag == 2 else 'F'
            next_key = getattr(self, '_cont_next_key', '')

            # TR 코드에 따른 REST API 호출 (키움 REST API는 body를 직접 전달)
            response = self.rest_client.request(api_id, rest_params, cont_yn=cont_yn, next_key=next_key)
            self._tr_response = response
            self._tr_rqname = rqname
            self._tr_trcode = trcode

            # TR 응답 데이터를 self.ohlcv 등에 파싱
            self._parse_tr_response(rqname, trcode, response)

            # 연속조회 여부 (ka10081/ka10080 은 응답 헤더의 cont-yn / next-key 사용)
            resp_cont_yn = response.get('_cont_yn', response.get('cont', 'F'))
            if resp_cont_yn in ('Y', 'T') or response.get('next', False):
                self.remained_data = True
                # 다음 연속조회에 사용할 next_key 저장
                self._cont_next_key = response.get('_next_key', response.get('next_key', ''))
            else:
                self.remained_data = False
                self._cont_next_key = ''

            time.sleep(TR_REQ_TIME_INTERVAL)
            return 0

        except RateLimitExceeded:
            raise
        except Exception as e:
            logger.critical(f"TR 요청 실패 [{trcode}]: {e}")
            self.remained_data = False
            return -1

    def _tr_input_map(self, trcode, input_values):
        """기존 SetInputValue 의 한글 키를 REST API 파라미터로 매핑"""
        mapping = {
            '종목코드': 'stk_cd',
            '기준일자': 'base_dt',
            '수정주가구분': 'upd_stkpc_tp',
            '틱범위': 'tic_scope',
            '계좌번호': 'acno',
            '시작일자': 'strt_dt',
            '종료일자': 'end_dt',
            '비밀번호': 'pwd',
            '비밀번호입력매체': 'pwd_iv',
        }
        result = {}
        for k, v in input_values.items():
            key = mapping.get(k, k)
            result[key] = str(v)
        return result

    def _parse_tr_response(self, rqname, trcode, response):
        """REST API 응답을 기존 TR 데이터 형식으로 파싱"""
        # opt10081: 주식일봉차트조회
        if rqname == 'opt10081_req':
            self._parse_opt10081(response)
        # opt10080: 주식분봉차트조회
        elif rqname == 'opt10080_req':
            self._parse_opt10080(response)
        # opw00001: 예수금상세현황조회
        elif rqname == 'opw00001_req':
            self._parse_opw00001(response)
        # opw00018: 계좌평가잔고내역조회
        elif rqname == 'opw00018_req':
            self._parse_opw00018(response)
        # opt10073: 당일실현손익요청
        elif rqname == 'opt10073_req':
            self._parse_opt10073(response)
        # opt10074: 당일매매성과요청
        elif rqname == 'opt10074_req':
            self._parse_opt10074(response)
        # opw00015: 계좌별주문체결내역조회
        elif rqname == 'opw00015_req':
            self._parse_opw00015(response)
        # opt10076: 당일주문체결내역요청
        elif rqname == 'opt10076_req':
            self._parse_opt10076(response)
        # opt10001: 주식기본정보요청
        elif rqname == 'opt10001_req':
            self._parse_opt10001(response)

    def _parse_opt10081(self, response):
        """주식일봉차트조회 응답 파싱 (ka10081: stk_dt_pole_chart_qry)
        주의: 연속조회 시 데이터가 누적되어야 하므로 self.ohlcv 를 초기화하지 않는다.
              초기화는 get_total_data() 시작 시 수행한다.
        """
        rows = response.get('stk_dt_pole_chart_qry', [])
        if not rows:
            rows = response.get('stk_dt_pole_qry', [])  # 이전 응답 형식 호환
        if not rows:
            rows = response.get('output', [])
        if isinstance(rows, dict):
            rows = [rows]

        for row in rows:
            # ka10081 응답 키: dt, open_pric, high_pric, low_pric, cur_prc, trde_qty
            # (2026-08-13 수정) REST API는 원화 가격을 그대로 반환하므로 /10 처리 금지
            self.ohlcv['date'].append(str(row.get('dt', row.get('일자', ''))))
            self.ohlcv['open'].append(int(row.get('open_pric', row.get('open_prc', row.get('시가', 0)))))
            self.ohlcv['high'].append(int(row.get('high_pric', row.get('high_prc', row.get('고가', 0)))))
            self.ohlcv['low'].append(int(row.get('low_pric', row.get('low_prc', row.get('저가', 0)))))
            self.ohlcv['close'].append(int(row.get('cur_prc', row.get('현재가', 0))))
            self.ohlcv['volume'].append(int(row.get('trde_qty', row.get('tr_vol', row.get('거래량', 0))) or 0))

    def _parse_opt10080(self, response):
        """주식분봉차트조회 응답 파싱 (ka10080)
        실제 REST 응답: {"stk_min_pole_chart_qry": [...], ...}
        - 행의 날짜 필드명: cntr_tm (체결시간, YYYYMMDDHHMMSS)
        - 가격 필드: open_pric/high_pric/low_pric/cur_prc (원화), 거래량: trde_qty
        주의: 연속조회 시 데이터가 누적되어야 하므로 self.ohlcv 를 초기화하지 않는다.
              초기화는 get_total_data_min() 시작 시 수행한다.
        """
        rows = response.get('stk_min_pole_chart_qry', [])
        if not rows:
            rows = response.get('stk_min_pole_qry', [])
        if not rows:
            rows = response.get('output', [])
        if isinstance(rows, dict):
            rows = [rows]

        # 빈 가격값('')이 오면 int() 변환 실패 → 안전 처리
        def _safe_int(val, default=0):
            s = str(val).strip()
            if not s:
                return default
            try:
                return int(s)
            except (ValueError, TypeError):
                return default

        for row in rows:
            # 체결시간(cntr_tm)은 14자리(YYYYMMDDHHMMSS) → OCX와 동일하게 12자리(YYYYMMDDHHMM)로 저장
            # (set_min_crawler_table 의 sum_volume 일자전환 로직이 12자리 기준)
            # (2026-08-13 수정) REST API는 원화 가격을 그대로 반환하므로 /10 처리 금지
            dt_val = str(row.get('cntr_tm', row.get('dt', row.get('체결시간', ''))))
            if not dt_val:
                continue  # 날짜 없으면 무효 행 스킵
            self.ohlcv['date'].append(dt_val[:-2] if len(dt_val) == 14 else dt_val)
            self.ohlcv['open'].append(abs(_safe_int(row.get('open_pric', row.get('open_prc', 0)))))
            self.ohlcv['high'].append(abs(_safe_int(row.get('high_pric', row.get('high_prc', 0)))))
            self.ohlcv['low'].append(abs(_safe_int(row.get('low_pric', row.get('low_prc', 0)))))
            self.ohlcv['close'].append(abs(_safe_int(row.get('cur_prc', 0))))
            self.ohlcv['volume'].append(_safe_int(row.get('trde_qty', row.get('tr_vol', 0))))
            self.ohlcv['sum_volume'].append(int(0))

    def _parse_opw00001(self, response):
        """예수금상세현황조회 응답 파싱 (키움 REST API output1 형식)"""
        data = response.get('output1', response.get('dpsa_dtl_stt_qry', response.get('output', {})))
        if isinstance(data, list) and data:
            data = data[0]

        self.d2_deposit = data.get('dps', data.get('예수금', '0'))
        self.d2_deposit_before_format = data.get('dps', data.get('예수금', '0'))
        try:
            self.d2_deposit_before_format = str(int(self.d2_deposit_before_format))
        except (ValueError, TypeError):
            self.d2_deposit_before_format = '0'

    def _parse_opw00018(self, response):
        """계좌평가잔고내역조회 응답 파싱 (키움 REST API output1/output2 형식)"""
        # 1차원 데이터 (계좌 요약)
        summary = response.get('output1', response.get('acno_evlu_bal_tot_qry', {}))
        if isinstance(summary, list) and summary:
            summary = summary[0]

        # 2차원 데이터 (종목별 상세)
        detail = response.get('output2', response.get('acno_evlu_bal_tot_dtl_qry', []))
        if isinstance(detail, dict):
            detail = [detail]

        self.opw00018_output = {'single': {}, 'multi': []}

        if summary:
            self.opw00018_output['single'] = {
                'd2_deposit': summary.get('dps', summary.get('예수금', '0')),
                'total_purchase_price': summary.get('tot_pch_amt', summary.get('총매입금액', '0')),
                'total_eval_price': summary.get('tot_evlu_amt', summary.get('총평가금액', '0')),
                'total_eval_profit_loss_price': summary.get('tot_evlu_pl_amt', summary.get('총평가손익금액', '0')),
                'total_earning_rate': summary.get('tot_ern_rt', summary.get('총수익률', '0')),
                'estimated_deposit': summary.get('extr_dps', summary.get('추정예수금', '0')),
            }

            # self 속성으로도 반영 (기존 open_api.py 코드 호환)
            self.total_purchase_price = summary.get('tot_pch_amt', summary.get('총매입금액', '0'))
            self.total_eval_price = summary.get('tot_evlu_amt', summary.get('총평가금액', '0'))
            self.total_eval_profit_loss_price = summary.get('tot_evlu_pl_amt', summary.get('총평가손익금액', '0'))
            self.change_total_purchase_price = summary.get('tot_pch_amt', summary.get('총매입금액', '0'))
            self.change_total_eval_price = summary.get('tot_evlu_amt', summary.get('총평가금액', '0'))
            self.change_total_eval_profit_loss_price = summary.get('tot_evlu_pl_amt', summary.get('총평가손익금액', '0'))
            self.change_total_earning_rate = summary.get('tot_ern_rt', summary.get('총수익률', '0'))
            self.change_estimated_deposit = summary.get('extr_dps', summary.get('추정예수금', '0'))
            self.today_profit = '0'
            self.total_profit = '0'
        else:
            # REST API 오류 시 0으로 초기화 (AttributeError 방지)
            self.total_purchase_price = '0'
            self.total_eval_price = '0'
            self.total_eval_profit_loss_price = '0'
            self.change_total_purchase_price = '0'
            self.change_total_eval_price = '0'
            self.change_total_eval_profit_loss_price = '0'
            self.change_total_earning_rate = '0'
            self.change_estimated_deposit = '0'
            self.today_profit = '0'
            self.total_profit = '0'

        if detail:
            for row in detail:
                self.opw00018_output['multi'].append((
                    row.get('stk_nm', row.get('종목명', '')),
                    row.get('bal_qty', row.get('보유수량', '0')),
                    row.get('pch_prc', row.get('매입가', '0')),
                    row.get('cur_prc', row.get('현재가', '0')),
                    row.get('evlu_pl', row.get('평가손익', '0')),
                    row.get('ern_rt', row.get('수익률', '0')),
                    row.get('pch_amt', row.get('매입금액', '0')),
                    row.get('stk_cd', row.get('종목코드', '')),
                ))

    def _parse_opt10073(self, response):
        """당일실현손익요청 응답 파싱"""
        self.opt10073_output = {'multi': []}
        rows = response.get('tdy_rl_pl_qry', response.get('output', []))
        if isinstance(rows, dict):
            rows = [rows]

        for row in rows:
            self.opt10073_output['multi'].append((
                str(row.get('dt', row.get('일자', ''))),
                str(row.get('stk_cd', row.get('종목코드', ''))),
                str(row.get('stk_nm', row.get('종목명', ''))),
                str(row.get('ccld_qty', row.get('체결수량', '0'))),
                str(row.get('rl_pl', row.get('실현손익', '0'))),
                str(row.get('ern_rt', row.get('수익률', '0'))),
            ))

    def _parse_opt10074(self, response):
        """당일매매성과요청 응답 파싱"""
        self.opt10074_output = {'multi': []}
        rows = response.get('tdy_tr_prfm_qry', response.get('output', []))
        if isinstance(rows, dict):
            rows = [rows]

        for row in rows:
            self.opt10074_output['multi'].append(row)

    def _parse_opw00015(self, response):
        """계좌별주문체결내역조회 응답 파싱"""
        self.opw00015_output = {'multi': []}
        rows = response.get('acno_ord_ccld_tl_qry', response.get('output', []))
        if isinstance(rows, dict):
            rows = [rows]

        for row in rows:
            self.opw00015_output['multi'].append(row)

    def _parse_opt10076(self, response):
        """당일주문체결내역요청 응답 파싱"""
        self.opt10076_output = {'multi': []}
        rows = response.get('tdy_ord_ccld_tl_qry', response.get('output', []))
        if isinstance(rows, dict):
            rows = [rows]

        for row in rows:
            self.opt10076_output['multi'].append(row)

    def _parse_opt10001(self, response):
        """주식기본정보요청 응답 파싱 (영문 키 → 한글 키 변환 포함)"""
        data = response
        if not isinstance(data, dict):
            self.opt10001_output = {}
            return

        # 응답 래핑 키(stk_bsic_info_qry / output 등)가 있으면 그 안의 데이터를 사용
        for key in ('stk_bsic_info_qry', 'output', 'output1', 'data'):
            val = data.get(key)
            if isinstance(val, (dict, list)) and val:
                data = val
                break

        if isinstance(data, list) and data:
            data = data[0]
        if not isinstance(data, dict):
            self.opt10001_output = {}
            return

        # 영문 키를 한글 키로 변환 (매핑에 없는 키는 그대로 유지)
        converted = {}
        for k, v in data.items():
            converted[REST_FINANCE_KEY_MAP.get(k, k)] = v
        self.opt10001_output = converted

    def _log_finance_keys_once(self, data):
        """ka10001 실제 응답 키를 1회만 로그로 남겨 매핑 정확도를 높인다."""
        if getattr(self, '_finance_keys_logged', False):
            return
        self._finance_keys_logged = True
        logger.info(f'[INFO] ka10001 응답 키 목록: {list(data.keys())}')
        logger.info(f'[INFO] ka10001 응답 샘플: {str(data)[:300]}')

    # ──────────────────────────────────────────────
    #  GetCommData / GetRepeatCnt 구현
    # ──────────────────────────────────────────────
    def _get_comm_data_rest(self, trcode, rqname, index, item_name):
        """REST API 응답에서 특정 데이터 추출"""
        # item_name(한글)을 REST API 응답 키로 매핑
        if not hasattr(self, '_tr_response'):
            return ''

        response = self._tr_response
        data = response

        # output 배열에서 index 번째 row 추출
        for key in [f'{trcode.lower()}_qry', 'output', 'output1', 'output2']:
            if key in response:
                data = response[key]
                break

        if isinstance(data, list):
            if index < len(data):
                data = data[index]
            elif data:
                data = data[0]
            else:
                return ''
        elif isinstance(data, dict):
            pass
        else:
            return ''

        # 한글 필드명 매핑
        field_map = {
            '일자': ['dt', '일자'],
            '시가': ['open_prc', '시가'],
            '고가': ['high_prc', '고가'],
            '저가': ['low_prc', '저가'],
            '현재가': ['cur_prc', '현재가'],
            '거래량': ['tr_vol', '거래량'],
            '종목코드': ['stk_cd', '종목코드'],
            '종목명': ['stk_nm', '종목명'],
            '체결시간': ['dt', '체결시간'],
        }

        keys = field_map.get(item_name, [item_name])
        for k in keys:
            if k in data:
                val = str(data[k])
                return val.strip() if val else ''

        return ''

    def _get_repeat_cnt_rest(self, trcode, rqname):
        """REST API 응답의 반복 데이터 개수 반환"""
        if not hasattr(self, '_tr_response'):
            return 0

        response = self._tr_response
        for key in [f'{trcode.lower()}_qry', 'output', 'output1', 'output2']:
            if key in response:
                data = response[key]
                if isinstance(data, list):
                    return len(data)
                elif isinstance(data, dict):
                    return 1
        return 0

    # ──────────────────────────────────────────────
    #  종목 정보 REST API 메서드
    # ──────────────────────────────────────────────
    def _get_code_list_by_market_rest(self, market):
        """시장별 종목코드 리스트 (REST API)"""
        # 키움 REST API: ka10001 (전종목기본조회) 또는 별도 API
        # REST API에서 시장별 종목 리스트를 직접 제공하지 않는 경우
        # DB의 stock_item_all 테이블에서 조회
        try:
            market_map = {'0': 'stockMkt', '10': 'kosdaqMkt', '50': 'konexMkt', '8': 'etf'}
            sql = "SELECT code FROM stock_item_all"
            if market in ('0', '10', '50'):
                sql += f" WHERE code IN (SELECT code FROM stock_{'kospi' if market == '0' else 'kosdaq' if market == '10' else 'konex'})"
            rows = self.engine_daily_buy_list.execute(sql).fetchall()
            return ';'.join([row[0] for row in rows])
        except Exception:
            return ''

    def _get_master_code_name_rest(self, code):
        """종목명 조회 (REST API) - shelve 파일 캐시 + rate limit(429) 지수 백오프 재시도"""
        # 0. 진행 상황 로그 (멈춤 오해 방지: 10개마다 출력)
        if not hasattr(self, '_name_lookup_count'):
            self._name_lookup_count = 0
        self._name_lookup_count += 1
        if self._name_lookup_count % 10 == 0:
            logger.info(f"[PROGRESS] 종목명 조회 진행 중... {self._name_lookup_count}번째 호출 (code={code})")

        # 1. shelve 파일 캐시 확인 (이미 조회한 종목명 재사용 - rate limit 방지)
        import shelve
        cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ka10001_cache.db')
        cache_path = os.path.abspath(cache_path)
        try:
            with shelve.open(cache_path) as cache:
                if code in cache and cache[code]:
                    return cache[code]
        except Exception:
            pass

        # 2. REST API(ka10001)로 직접 종목명 조회
        #    - rate limit(유량=1, 초당 1회) 대응: 호출 전 항상 1초 대기
        #    - 429 발생 시 지수 백오프 재시도 (최대 5회)
        #    - DB 조회 단계는 제거 (stock_item_all이 아직 없을 때 DB 접근 지연 방지)
        max_retries = 5
        base_backoff = 1.0
        for attempt in range(1, max_retries + 1):
            try:
                # rate limit 방지: 호출 전 1초 대기 (유량=1 이므로 반드시 필요)
                time.sleep(1.0)
                response = self.rest_client.request('ka10001', {'stk_cd': code})
                # ka10001 응답: {"stk_cd": "005930", "stk_nm": "삼성전자", ...} - 최상위 키
                code_name = str(response.get('stk_nm', response.get('종목명', ''))).strip()
                # 성공 시 캐시에 저장
                if code_name:
                    try:
                        with shelve.open(cache_path) as cache:
                            cache[code] = code_name
                    except Exception:
                        pass
                return code_name
            except RateLimitExceeded:
                backoff = base_backoff * (2 ** (attempt - 1))
                logger.warning(f"[WARN] ka10001 rate limit ({code}). 대기 {backoff}s 후 재시도 {attempt}/{max_retries}")
                time.sleep(backoff)
                continue
            except Exception:
                # 기타 오류는 바로 빈 문자열 반환 (원본 전략 유지)
                return ''

        # 모든 재시도 실패
        logger.error(f"[ERROR] {code} 종목명 조회 모든 재시도 실패")
        return ''

    def _get_master_listed_stock_cnt_rest(self, code):
        """상장주식수 조회 (REST API)"""
        try:
            response = self.rest_client.request('ka10001', {'stk_cd': code})
            data = response.get('stk_bsic_info_qry', response.get('output', {}))
            if isinstance(data, list) and data:
                data = data[0]
            return str(data.get('lstg_stk_cnt', data.get('상장주수', '0')))
        except Exception:
            return '0'

    def _get_master_construction_rest(self, code):
        """감리구분 조회 (REST API)"""
        try:
            response = self.rest_client.request('ka10001', {'stk_cd': code})
            data = response.get('stk_bsic_info_qry', response.get('output', {}))
            if isinstance(data, list) and data:
                data = data[0]
            return str(data.get('cr', data.get('감리구분', '0')))
        except Exception:
            return '0'

    def _get_master_stock_state_rest(self, code):
        """증거금비율, 거래정지여부 등 조회 (REST API)"""
        try:
            response = self.rest_client.request('ka10001', {'stk_cd': code})
            data = response.get('stk_bsic_info_qry', response.get('output', {}))
            if isinstance(data, list) and data:
                data = data[0]
            # 증거금비율;거래정지여부;관리종목여부 형식으로 반환
            margin = str(data.get('sgrn_rt', data.get('증거금비율', '100')))
            trade_stop = str(data.get('tr_stop_yn', data.get('거래정지여부', 'N')))
            managing = str(data.get('mgmt_stk_yn', data.get('관리종목여부', 'N')))
            return f'{margin};{trade_stop};{managing}'
        except Exception:
            return '100;N;N'

    def _get_theme_group_list_rest(self):
        """테마그룹 리스트 (REST API)"""
        # 키움 REST API에서 테마 관련 API가 제공되지 않는 경우 빈 문자열 반환
        logger.debug("REST API에서는 테마그룹 리스트를 지원하지 않습니다.")
        return ''

    def _get_theme_group_code_rest(self, theme_code):
        """테마그룹 종목코드 (REST API)"""
        logger.debug("REST API에서는 테마그룹 종목코드를 지원하지 않습니다.")
        return ''

    def _get_master_stock_info_rest(self, code):
        """주식종목 정보 (REST API)"""
        try:
            response = self.rest_client.request('ka10001', {'stk_cd': code})
            data = response.get('stk_bsic_info_qry', response.get('output', {}))
            if isinstance(data, list) and data:
                data = data[0]
            # 시장구분;종목분류 등 형식으로 반환
            market = str(data.get('mrkt_tp', data.get('시장구분', '')))
            category = str(data.get('stk_tp', data.get('종목구분', '')))
            return f'{market};{category}'
        except Exception:
            return ';'

    def _koa_functions_rest(self, func_name, code):
        """KOA_Functions 특수함수 (REST API)"""
        logger.debug(f"KOA_Functions: {func_name}, {code}")
        if func_name == 'GetMasterStockInfo':
            return self._get_master_stock_info_rest(code)
        return ''

    # ──────────────────────────────────────────────
    #  주문 관련 (REST API)
    # ──────────────────────────────────────────────
    def _send_order_rest(self, *args):
        """주문 전송 (REST API)"""
        # SendOrder 인자: rqname, screen_no, acc_no, order_type, code, quantity, price, hoga, order_no
        rqname = args[0] if len(args) > 0 else ''
        screen_no = args[1] if len(args) > 1 else ''
        acc_no = args[2] if len(args) > 2 else ''
        order_type = args[3] if len(args) > 3 else 1
        code = args[4] if len(args) > 4 else ''
        quantity = args[5] if len(args) > 5 else 0
        price = args[6] if len(args) > 6 else 0
        hoga = args[7] if len(args) > 7 else '00'
        order_no = args[8] if len(args) > 8 else ''

        # REST API 주문 파라미터 매핑
        params = {
            'acno': acc_no,
            'pwd': '0000',  # 모의투자 비밀번호
            'ord_tp': str(order_type),
            'stk_cd': code,
            'ord_qty': str(quantity),
            'ord_prc': str(price),
            'trd_tp': hoga,
        }

        try:
            response = self.rest_client.request_order('kt00001', params)
            logger.debug(f"주문 전송 완료: {response}")
            return 0
        except Exception as e:
            logger.critical(f"주문 전송 실패: {e}")
            return -1

    def _get_chejan_data_rest(self, fid):
        """체결 데이터 조회 (REST API)"""
        # REST API에서는 실시간 체결 데이터를 별도로 조회해야 함
        # 기본적으로 빈 문자열 반환
        return ''

    # ──────────────────────────────────────────────
    #  set_input_value / comm_rq_data 래퍼
    # ──────────────────────────────────────────────
    def set_input_value(self, id, value):
        if not hasattr(self, '_input_values'):
            self._input_values = {}
        self._input_values[id] = value

    def comm_rq_data(self, rqname, trcode, next, screen_no):
        return self._comm_rq_data_rest(rqname, trcode, next, screen_no)

    def _get_comm_data(self, code, field_name, index, item_name):
        return self._get_comm_data_rest(code, field_name, index, item_name)

    def _get_repeat_cnt(self, trcode, rqname):
        return self._get_repeat_cnt_rest(trcode, rqname)

    # ──────────────────────────────────────────────
    #  setting_data 초기화 (open_api.py 와 동일)
    # ──────────────────────────────────────────────
    def init_db_setting_data(self):
        logger.debug("init_db_setting_data !! ")
        df_setting_data_temp = {'loan_money': [], 'limit_money': [], 'invest_unit': [], 'max_invest_unit': [],
                                'min_invest_unit': [],
                                'set_invest_unit': [], 'code_update': [], 'today_buy_stop': [],
                                'jango_data_db_check': [], 'possessed_item': [], 'today_profit': [],
                                'final_chegyul_check': [],
                                'db_to_buy_list': [], 'today_buy_list': [], 'daily_crawler': [],
                                'daily_buy_list': []}

        df_setting_data = DataFrame(df_setting_data_temp,
                                    columns=['loan_money', 'limit_money', 'invest_unit', 'max_invest_unit',
                                             'min_invest_unit',
                                             'set_invest_unit', 'code_update', 'today_buy_stop',
                                             'jango_data_db_check', 'possessed_item', 'today_profit',
                                             'final_chegyul_check',
                                             'db_to_buy_list', 'today_buy_list', 'daily_crawler',
                                             'daily_buy_list'])

        df_setting_data.loc[0, 'loan_money'] = int(0)
        df_setting_data.loc[0, 'limit_money'] = int(0)
        df_setting_data.loc[0, 'invest_unit'] = int(0)
        df_setting_data.loc[0, 'max_invest_unit'] = int(0)
        df_setting_data.loc[0, 'min_invest_unit'] = int(0)

        df_setting_data.loc[0, 'set_invest_unit'] = str(0)
        df_setting_data.loc[0, 'code_update'] = str(0)
        df_setting_data.loc[0, 'today_buy_stop'] = str(0)
        df_setting_data.loc[0, 'jango_data_db_check'] = str(0)

        df_setting_data.loc[0, 'possessed_item'] = str(0)
        df_setting_data.loc[0, 'today_profit'] = str(0)
        df_setting_data.loc[0, 'final_chegyul_check'] = str(0)
        df_setting_data.loc[0, 'db_to_buy_list'] = str(0)
        df_setting_data.loc[0, 'today_buy_list'] = str(0)
        df_setting_data.loc[0, 'daily_crawler'] = str(0)
        df_setting_data.loc[0, 'min_crawler'] = str(0)
        df_setting_data.loc[0, 'daily_buy_list'] = str(0)

        df_setting_data.to_sql('setting_data', self.engine_JB, if_exists='replace')

    # ──────────────────────────────────────────────
    #  all_item_db 추가 (open_api.py 와 동일)
    # ──────────────────────────────────────────────
    def db_to_all_item(self, order_num, code, chegyul_check, purchase_price, rate):
        logger.debug("db_to_all_item 함수에 들어왔다!!!")
        self.date_setting()
        self.sf.init_df_all_item()
        self.sf.df_all_item.loc[0, 'order_num'] = order_num
        self.sf.df_all_item.loc[0, 'code'] = str(code)
        self.sf.df_all_item.loc[0, 'rate'] = float(rate)

        self.sf.df_all_item.loc[0, 'buy_date'] = self.today_detail
        self.sf.df_all_item.loc[0, 'chegyul_check'] = chegyul_check
        self.sf.df_all_item.loc[0, 'reinvest_date'] = '#'
        self.sf.df_all_item.loc[0, 'invest_unit'] = self.invest_unit
        self.sf.df_all_item.loc[0, 'purchase_price'] = purchase_price

        if order_num != 0:
            recent_daily_buy_list_date = self.sf.get_recent_daily_buy_list_date()
            if recent_daily_buy_list_date:
                df = self.sf.get_daily_buy_list_by_code(code, recent_daily_buy_list_date)
                if not df.empty:
                    self.sf.df_all_item.loc[0, 'code_name'] = df.loc[0, 'code_name']
                    self.sf.df_all_item.loc[0, 'close'] = df.loc[0, 'close']
                    self.sf.df_all_item.loc[0, 'open'] = df.loc[0, 'open']
                    self.sf.df_all_item.loc[0, 'high'] = df.loc[0, 'high']
                    self.sf.df_all_item.loc[0, 'low'] = df.loc[0, 'low']
                    self.sf.df_all_item.loc[0, 'volume'] = df.loc[0, 'volume']
                    self.sf.df_all_item.loc[0, 'd1_diff_rate'] = float(df.loc[0, 'd1_diff_rate'])
                    self.sf.df_all_item.loc[0, 'clo5'] = df.loc[0, 'clo5']
                    self.sf.df_all_item.loc[0, 'clo10'] = df.loc[0, 'clo10']
                    self.sf.df_all_item.loc[0, 'clo20'] = df.loc[0, 'clo20']
                    self.sf.df_all_item.loc[0, 'clo40'] = df.loc[0, 'clo40']
                    self.sf.df_all_item.loc[0, 'clo60'] = df.loc[0, 'clo60']
                    self.sf.df_all_item.loc[0, 'clo80'] = df.loc[0, 'clo80']
                    self.sf.df_all_item.loc[0, 'clo100'] = df.loc[0, 'clo100']
                    self.sf.df_all_item.loc[0, 'clo120'] = df.loc[0, 'clo120']

                    if df.loc[0, 'clo5_diff_rate'] is not None:
                        self.sf.df_all_item.loc[0, 'clo5_diff_rate'] = float(df.loc[0, 'clo5_diff_rate'])
                    if df.loc[0, 'clo10_diff_rate'] is not None:
                        self.sf.df_all_item.loc[0, 'clo10_diff_rate'] = float(df.loc[0, 'clo10_diff_rate'])
                    if df.loc[0, 'clo20_diff_rate'] is not None:
                        self.sf.df_all_item.loc[0, 'clo20_diff_rate'] = float(df.loc[0, 'clo20_diff_rate'])
                    if df.loc[0, 'clo40_diff_rate'] is not None:
                        self.sf.df_all_item.loc[0, 'clo40_diff_rate'] = float(df.loc[0, 'clo40_diff_rate'])
                    if df.loc[0, 'clo60_diff_rate'] is not None:
                        self.sf.df_all_item.loc[0, 'clo60_diff_rate'] = float(df.loc[0, 'clo60_diff_rate'])
                    if df.loc[0, 'clo80_diff_rate'] is not None:
                        self.sf.df_all_item.loc[0, 'clo80_diff_rate'] = float(df.loc[0, 'clo80_diff_rate'])
                    if df.loc[0, 'clo100_diff_rate'] is not None:
                        self.sf.df_all_item.loc[0, 'clo100_diff_rate'] = float(df.loc[0, 'clo100_diff_rate'])
                    if df.loc[0, 'clo120_diff_rate'] is not None:
                        self.sf.df_all_item.loc[0, 'clo120_diff_rate'] = float(df.loc[0, 'clo120_diff_rate'])

        self.sf.df_all_item = self.sf.df_all_item.fillna(0)
        self.sf.df_all_item.to_sql('all_item_db', self.engine_JB, if_exists='append', dtype={
            'code_name': Text,
            'rate': Float,
            'sell_rate': Float,
            'purchase_rate': Float,
            'sell_date': Text,
            'd1_diff_rate': Float,
            'clo5_diff_rate': Float,
            'clo10_diff_rate': Float,
            'clo20_diff_rate': Float,
            'clo40_diff_rate': Float,
            'clo60_diff_rate': Float,
            'clo80_diff_rate': Float,
            'clo100_diff_rate': Float,
            'clo120_diff_rate': Float
        })

    # ──────────────────────────────────────────────
    #  잔고 확인 (REST API)
    # ──────────────────────────────────────────────
    def check_balance(self):
        logger.debug("check_balance 함수에 들어왔습니다!")
        self.reset_opw00018_output()

        self.set_input_value("계좌번호", self.account_number)
        self.comm_rq_data("opw00018_req", "opw00018", 0, "2000")

        while self.remained_data:
            self.set_input_value("계좌번호", self.account_number)
            self.comm_rq_data("opw00018_req", "opw00018", 2, "2000")

    def get_count_possesed_item(self):
        logger.debug("get_count_possesed_item!!!")
        sql = "select count(*) from possessed_item"
        rows = self.engine_JB.execute(sql).fetchall()
        return rows[0][0]

    def setting_data_possesed_item(self):
        sql = "UPDATE setting_data SET possessed_item='%s' limit 1"
        self.engine_JB.execute(sql % (self.today))

    def db_to_possesed_item(self):
        logger.debug("db_to_possesed_item 함수에 들어왔습니다!")
        item_count = len(self.opw00018_output['multi'])
        possesed_item_temp = {'date': [], 'code': [], 'code_name': [], 'holding_amount': [], 'puchase_price': [],
                              'present_price': [], 'valuation_profit': [], 'rate': [], 'item_total_purchase': []}

        possesed_item = DataFrame(possesed_item_temp,
                                  columns=['date', 'code', 'code_name', 'holding_amount', 'puchase_price',
                                           'present_price', 'valuation_profit', 'rate', 'item_total_purchase'])

        for i in range(item_count):
            row = self.opw00018_output['multi'][i]
            possesed_item.loc[i, 'date'] = self.today
            possesed_item.loc[i, 'code'] = row[7]
            possesed_item.loc[i, 'code_name'] = row[0]
            possesed_item.loc[i, 'holding_amount'] = int(row[1])
            possesed_item.loc[i, 'puchase_price'] = int(row[2])
            possesed_item.loc[i, 'present_price'] = int(row[3])
            possesed_item.loc[i, 'valuation_profit'] = int(row[4])
            possesed_item.loc[i, 'rate'] = float(row[5])
            possesed_item.loc[i, 'item_total_purchase'] = int(row[6])

        possesed_item.to_sql('possessed_item', self.engine_JB, if_exists='replace')
        self.chegyul_sync()

    # ──────────────────────────────────────────────
    #  분봉 데이터 조회 (REST API)
    # ──────────────────────────────────────────────
    def get_total_data_min(self, code, code_name, start):
        self.ohlcv = defaultdict(list)
        self._cont_next_key = ''   # 연속조회 키 초기화

        self.set_input_value("종목코드", code)
        self.set_input_value("틱범위", 1)
        self.set_input_value("수정주가구분", 1)

        self.craw_table_exist = False

        if self.is_min_craw_table_exist(code_name):
            self.craw_table_exist = True
            self.craw_db_last_min = self.get_craw_db_last_min(code_name)
            self.craw_db_last_min_sum_volume = self.get_craw_db_last_min_sum_volume(code_name)
        else:
            self.craw_db_last_min = str(0)
            self.craw_db_last_min_sum_volume = 0

        # rate limit 방지: 호출 전 1초 대기 (ka10080 유량=1, 초당 1회)
        time.sleep(1.0)

        # 429(rate limit) 시 재시도 (최대 5회, 지수 백오프)
        max_retries = 5
        base_backoff = 1.0
        for attempt in range(1, max_retries + 1):
            try:
                self.comm_rq_data("opt10080_req", "opt10080", 0, "1999")
                break
            except RateLimitExceeded:
                backoff = base_backoff * (2 ** (attempt - 1))
                logger.warning(f"[WARN] ka10080 rate limit ({code_name}). 대기 {backoff}s 후 재시도 {attempt}/{max_retries}")
                time.sleep(backoff)
                self.ohlcv = defaultdict(list)
                continue

        # 연속조회 (ka10080 은 한 번에 일정 건수씩 반환하므로 next-key 로 계속 조회)
        cont_count = 0
        max_cont = 20
        while self.remained_data == True and cont_count < max_cont:
            time.sleep(1.0)  # rate limit 방지 (유량=1)
            self.set_input_value("종목코드", code)
            self.set_input_value("틱범위", 1)
            self.set_input_value("수정주가구분", 1)
            self.comm_rq_data("opt10080_req", "opt10080", 2, "1999")
            cont_count += 1
            logger.debug(f"연속조회 {cont_count}회차 ({code_name}) - 누적 {len(self.ohlcv['date'])}건")

            # 빈 데이터 방지 (date 리스트가 비어있으면 [-1] 접근 시 IndexError)
            if not self.ohlcv or len(self.ohlcv.get('date', [])) == 0:
                break
            if self.ohlcv['date'][-1] < self.craw_db_last_min:
                break

        time.sleep(TR_REQ_TIME_INTERVAL)

        if len(self.ohlcv['date']) == 0 or self.ohlcv['date'][0] == '':
            return []
        if self.ohlcv['date'] == '':
            return []

        df = DataFrame(self.ohlcv, columns=['date', 'open', 'high', 'low', 'close', 'volume', 'sum_volume'])

        # (2026-08-13 수정) 연속조회가 같은 데이터를 반복 반환해도 고유 날짜만 남긴다.
        # 이렇게 하면 next-key 가 정상 동작하지 않아도 DB에 중복이 쌓이지 않는다.
        df = df.drop_duplicates(subset='date', keep='first')
        df = df.sort_values(by='date', ascending=True).reset_index(drop=True)
        return df

    # ──────────────────────────────────────────────
    #  일봉 데이터 조회 (REST API)
    #  - ka10081 rate limit(유량=1) 대응: 호출 전 1초 대기 + 429 재시도
    # ──────────────────────────────────────────────
    def get_total_data(self, code, code_name, date):
        logger.debug("get_total_data 함수에 들어왔다!")

        self.ohlcv = defaultdict(list)
        self._cont_next_key = ''   # 연속조회 키 초기화
        self.set_input_value("종목코드", code)
        self.set_input_value("기준일자", date)
        self.set_input_value("수정주가구분", 1)

        # rate limit 방지: 호출 전 1초 대기 (유량=1)
        time.sleep(1.0)

        # 429(rate limit) 시 재시도 (최대 5회, 지수 백오프)
        max_retries = 5
        base_backoff = 1.0
        for attempt in range(1, max_retries + 1):
            try:
                self.comm_rq_data("opt10081_req", "opt10081", 0, "0101")
                break
            except RateLimitExceeded:
                backoff = base_backoff * (2 ** (attempt - 1))
                logger.warning(f"[WARN] ka10081 rate limit ({code_name}). 대기 {backoff}s 후 재시도 {attempt}/{max_retries}")
                time.sleep(backoff)
                self.ohlcv = defaultdict(list)
                continue

        # 연속조회 (ka10081 은 한 번에 600건씩 반환하므로 next-key 로 계속 조회)
        # 최대 20회 연속조회 방지 (600건 x 20 = 12000일)
        cont_count = 0
        max_cont = 20
        while self.remained_data == True and cont_count < max_cont:
            time.sleep(1.0)  # rate limit 방지
            self.set_input_value("종목코드", code)
            self.set_input_value("기준일자", date)
            self.set_input_value("수정주가구분", 1)
            self.comm_rq_data("opt10081_req", "opt10081", 2, "0101")
            cont_count += 1
            logger.debug(f"연속조회 {cont_count}회차 ({code_name}) - 누적 {len(self.ohlcv['date'])}건")

        if len(self.ohlcv) == 0:
            return []
        if self.ohlcv['date'] == '':
            return []

        df = DataFrame(self.ohlcv, columns=['date', 'open', 'high', 'low', 'close', 'volume'])

        # (2026-08-09 수정) 연속조회가 같은 데이터를 반복 반환해도 고유 날짜만 남긴다.
        # 이렇게 하면 next-key 가 정상 동작하지 않아도 DB에 중복이 쌓이지 않는다.
        df = df.drop_duplicates(subset='date', keep='first')
        df = df.sort_values(by='date', ascending=True).reset_index(drop=True)

        return df

    # ──────────────────────────────────────────────
    #  테이블 존재 여부 확인 (open_api.py 와 동일)
    # ──────────────────────────────────────────────
    def is_craw_table_exist(self, code_name):
        sql = "select 1 from information_schema.tables where table_schema ='daily_craw' and table_name = '{}'"
        rows = self.engine_daily_craw.execute(sql.format(code_name)).fetchall()
        if rows:
            return True
        else:
            logger.debug(str(code_name) + " 테이블이 daily_craw db 에 없다. 새로 생성! ", )
            return False

    def is_min_craw_table_exist(self, code_name):
        sql = "select 1 from information_schema.tables where table_schema ='min_craw' and table_name = '{}'"
        rows = self.engine_craw.execute(sql.format(code_name)).fetchall()
        if rows:
            return True
        else:
            logger.debug(str(code_name) + " min_craw db에 없다 새로 생성! ", )
            return False

    def get_craw_db_last_min_sum_volume(self, code_name):
        sql = "SELECT sum_volume from `" + code_name + "` order by date desc limit 1"
        rows = self.engine_craw.execute(sql).fetchall()
        if len(rows):
            return rows[0][0]
        else:
            return str(0)

    def get_craw_db_last_min(self, code_name):
        sql = "SELECT date from `" + code_name + "` order by date desc limit 1"
        rows = self.engine_craw.execute(sql).fetchall()
        if len(rows):
            return rows[0][0]
        else:
            return str(0)

    def get_daily_craw_db_last_date(self, code_name):
        sql = "SELECT date from `" + code_name + "` order by date desc limit 1"
        rows = self.engine_daily_craw.execute(sql).fetchall()
        if len(rows):
            return rows[0][0]
        else:
            return str(0)

    # ──────────────────────────────────────────────
    #  특정 일 데이터 조회 (REST API)
    # ──────────────────────────────────────────────
    def get_one_day_option_data(self, code, start, option):
        self.ohlcv = defaultdict(list)

        self.set_input_value("종목코드", code)
        self.set_input_value("기준일자", start)
        self.set_input_value("수정주가구분", 1)

        self.comm_rq_data("opt10081_req", "opt10081", 0, "0101")

        if self.ohlcv['date'] == '':
            return False

        df = DataFrame(self.ohlcv, columns=['open', 'high', 'low', 'close', 'volume'], index=self.ohlcv['date'])

        if df.empty:
            return False

        try:
            logger.debug("get_one_day_option_data df : {} ".format(df))
            logger.debug("code : {},type(code): {}, start: {}, option: {} ".format(code, type(code), start, option))
            logger.debug("df.iloc[0, 3] (close) : {} ".format(df.iloc[0, 3]))
        except Exception as e:
            logger.critical(e)

        if option == 'open':
            return df.iloc[0, 0]
        elif option == 'high':
            return df.iloc[0, 1]
        elif option == 'low':
            return df.iloc[0, 2]
        elif option == 'close':
            return df.iloc[0, 3]
        elif option == 'volume':
            return df.iloc[0, 4]
        else:
            return False

    # ──────────────────────────────────────────────
    #  TR 데이터 파싱 (collector 용)
    # ──────────────────────────────────────────────
    def collector_opt10081(self, rqname, trcode):
        """collector 용 opt10081 파싱 (REST API 응답은 이미 _parse_opt10081 에서 처리됨)"""
        pass  # _parse_tr_response 에서 이미 self.ohlcv 에 데이터가 들어감

    def _opt10081(self, rqname, trcode):
        """trader 용 opt10081 파싱"""
        pass  # REST API 응답은 이미 파싱됨

    def _opt10080(self, rqname, trcode):
        pass

    def _opw00001(self, rqname, trcode):
        pass

    def _opw00018(self, rqname, trcode):
        pass

    def _opt10074(self, rqname, trcode):
        pass

    def _opw00015(self, rqname, trcode):
        pass

    def _opt10076(self, rqname, trcode):
        pass

    def _opt10073(self, rqname, trcode):
        pass

    def _opt10001(self, rqname, trcode):
        pass

    # ──────────────────────────────────────────────
    #  주문 전송 (REST API)
    # ──────────────────────────────────────────────
    def send_order(self, rqname, screen_no, acc_no, order_type, code, quantity, price, hoga, order_no):
        logger.debug("send_order!!!")
        try:
            self.exit_check()
            self._send_order_rest(rqname, screen_no, acc_no, order_type, code, quantity, price, hoga, order_no)
        except Exception as e:
            logger.critical(e)

    def get_chejan_data(self, fid):
        try:
            return self._get_chejan_data_rest(fid)
        except Exception as e:
            logger.critical(e)

    # ──────────────────────────────────────────────
    #  코드명 -> 종목코드 (open_api.py 와 동일)
    # ──────────────────────────────────────────────
    def codename_to_code(self, codename):
        sql = "select code from stock_item_all where code_name='%s'"
        rows = self.engine_daily_buy_list.execute(sql % (codename)).fetchall()
        if len(rows) != 0:
            return rows[0][0]

        logger.debug("code를 찾을 수 없다!! name이 긴놈이다!!!!")
        logger.debug(codename)

        sql = f"select code from stock_item_all where code_name like '{codename}%'"
        rows = self.engine_daily_buy_list.execute(sql).fetchall()

        if len(rows) != 0:
            return rows[0][0]

        logger.debug("codename이 존재하지 않는다 ..... 긴 것도 아니다...")
        return False

    def end_invest_count_check(self, code):
        logger.debug("end_invest_count_check 함수로 들어왔습니다!")
        logger.debug("end_invest_count_check_code!!!!!!!!")
        logger.debug(code)

        sql = "UPDATE all_item_db SET chegyul_check='%s' WHERE code='%s' and sell_date = '%s' ORDER BY buy_date desc LIMIT 1"
        self.engine_JB.execute(sql % (0, code, 0))

        sql = "delete from possessed_item where code ='%s'"
        self.engine_JB.execute(sql % (code,))

    def sell_chegyul_fail_check(self, code):
        logger.debug("sell_chegyul_fail_check 함수에 들어왔습니다!")
        logger.debug(code + " check!")
        sql = "UPDATE all_item_db SET chegyul_check='%s' WHERE code='%s' and sell_date = '%s' ORDER BY buy_date desc LIMIT 1"
        self.engine_JB.execute(sql % (1, code, 0))

    def buy_check_reset(self):
        logger.debug("buy_check_reset!!!")
        sql = "UPDATE setting_data SET today_buy_stop='%s' WHERE id='%s'"
        self.engine_JB.execute(sql % (0, 1))

    def buy_check_stop(self):
        logger.debug("buy_check_stop!!!")
        sql = "UPDATE setting_data SET today_buy_stop='%s' limit 1"
        self.engine_JB.execute(sql % (self.today))

    def jango_check(self):
        logger.debug("jango_check 함수에 들어왔습니다!")
        self.get_d2_deposit()
        try:
            if int(self.d2_deposit_before_format) > (int(self.sf.limit_money)):
                self.jango_is_null = False
                return True
            else:
                self.jango_is_null = True
                return False
        except Exception as e:
            logger.critical(e)
            self.jango_is_null = True
            return False

    # ──────────────────────────────────────────────
    #  예수금 조회 (REST API)
    # ──────────────────────────────────────────────
    def get_d2_deposit(self):
        logger.debug("get_d2_deposit 함수에 들어왔습니다!")
        self.reset_opw00018_output()
        self.set_input_value("계좌번호", self.account_number)
        self.comm_rq_data("opw00001_req", "opw00001", 0, "2000")

        # opw00001 응답에서 예수금 추출
        if hasattr(self, 'd2_deposit_before_format'):
            self.d2_deposit = self.change_format(self.d2_deposit_before_format)
        else:
            self.d2_deposit_before_format = '0'
            self.d2_deposit = '0'

    # ──────────────────────────────────────────────
    #  포맷 변환 함수들 (open_api.py 와 동일)
    # ──────────────────────────────────────────────
    def change_format(self, code):
        try:
            return format(int(code), ',')
        except (ValueError, TypeError):
            return '0'

    def change_format3(self, code):
        return code

    # ──────────────────────────────────────────────
    #  기타 메서드 (open_api.py 와 동일)
    # ──────────────────────────────────────────────
    def reset_opw00018_output(self):
        self.opw00018_output = {'single': {}, 'multi': []}

    def reset_opt10073_output(self):
        self.opt10073_output = {'multi': []}

    def get_connect_state(self):
        return 1  # REST API는 항상 연결됨

    def exit_check(self):
        """API 호출 횟수 체크"""
        if self.rq_count >= cf.max_api_call:
            logger.debug("max_api_call 도달. 프로그램을 종료합니다.")
            sys.exit(0)

    def py_check_balance(self):
        self.check_balance()

    def db_to_today_profit_list(self):
        logger.debug("db_to_today_profit_list!!!")
        self.reset_opt10073_output()
        self.set_input_value("계좌번호", self.account_number)
        self.set_input_value("시작일자", self.today)
        self.set_input_value("종료일자", self.today)
        self.comm_rq_data("opt10073_req", "opt10073", 0, "0328")

        while self.remained_data:
            self.set_input_value("계좌번호", self.account_number)
            self.comm_rq_data("opt10073_req", "opt10073", 2, "0328")

        today_profit_item_temp = {'date': [], 'code': [], 'code_name': [], 'amount': [], 'today_profit': [],
                                  'earning_rate': []}

        today_profit_item = DataFrame(today_profit_item_temp,
                                      columns=['date', 'code', 'code_name', 'amount', 'today_profit',
                                               'earning_rate'])

        item_count = len(self.opt10073_output['multi'])
        for i in range(item_count):
            row = self.opt10073_output['multi'][i]
            today_profit_item.loc[i, 'date'] = row[0]
            today_profit_item.loc[i, 'code'] = row[1]
            today_profit_item.loc[i, 'code_name'] = row[2]
            today_profit_item.loc[i, 'amount'] = int(row[3])
            today_profit_item.loc[i, 'today_profit'] = float(row[4])
            today_profit_item.loc[i, 'earning_rate'] = float(row[5])

        if len(today_profit_item) > 0:
            today_profit_item.to_sql('today_profit_list', self.engine_JB, if_exists='append')
        sql = "UPDATE setting_data SET today_profit='%s' limit 1"
        self.engine_JB.execute(sql % (self.today))

    def set_invest_unit(self):
        logger.debug("set_invest_unit!!!")
        self.get_d2_deposit()
        self.check_balance()
        # total_purchase_price가 없으면 0으로 처리 (REST API 응답에 따라)
        total_purchase = getattr(self, 'total_purchase_price', 0) or 0
        self.total_invest = self.change_format(
            str(int(self.d2_deposit_before_format or 0) + int(total_purchase)))
        self.invest_unit = self.sf.invest_unit
        sql = "UPDATE setting_data SET invest_unit='%s',set_invest_unit='%s' limit 1"
        self.engine_JB.execute(sql % (self.invest_unit, self.today))

    def db_to_jango(self):
        self.total_invest = self.change_format(
            str(int(self.d2_deposit_before_format) + int(self.total_purchase_price)))
        jango_temp = {'id': [], 'date': [], 'total_asset': [], 'today_profit': [], 'total_profit': [],
                      'total_invest': [], 'd2_deposit': [],
                      'today_purchase': [], 'today_evaluation': [],
                      'today_invest': [], 'today_rate': [],
                      'estimate_asset': []}

        jango_col_list = ['date', 'today_earning_rate', 'total_asset', 'today_profit', 'total_profit', 'total_invest',
                          'd2_deposit', 'today_purchase', 'today_evaluation', 'today_invest', 'today_rate',
                          'estimate_asset', 'volume_limit', 'ipo_term', 'reinvest_point', 'sell_point',
                          'max_reinvest_count', 'invest_limit_rate', 'invest_unit', 'min_invest_unit',
                          'max_invest_unit',
                          'avg_close_multiply_rate', 'max_reinvest_unit', 'rate_std_sell_point', 'limit_money',
                          'total_profitcut',
                          'total_losscut', 'total_profitcut_count', 'total_losscut_count', 'loan_money',
                          'start_kospi_point',
                          'start_kosdaq_point', 'end_kospi_point', 'end_kosdaq_point', 'today_buy_count',
                          'today_buy_total_sell_count',
                          'today_buy_total_possess_count', 'today_buy_today_profitcut_count',
                          'today_buy_today_profitcut_rate',
                          'today_buy_today_losscut_count', 'today_buy_today_losscut_rate',
                          'today_buy_total_profitcut_count', 'today_buy_total_profitcut_rate',
                          'today_buy_total_losscut_count',
                          'today_buy_total_losscut_rate', 'today_buy_reinvest_count0_sell_count',
                          'today_buy_reinvest_count1_sell_count', 'today_buy_reinvest_count2_sell_count',
                          'today_buy_reinvest_count3_sell_count', 'today_buy_reinvest_count4_sell_count',
                          'today_buy_reinvest_count4_sell_profitcut_count',
                          'today_buy_reinvest_count4_sell_losscut_count', 'today_buy_reinvest_count5_sell_count',
                          'today_buy_reinvest_count5_sell_profitcut_count',
                          'today_buy_reinvest_count5_sell_losscut_count',
                          'today_buy_reinvest_count0_remain_count',
                          'today_buy_reinvest_count1_remain_count', 'today_buy_reinvest_count2_remain_count',
                          'today_buy_reinvest_count3_remain_count', 'today_buy_reinvest_count4_remain_count',
                          'today_buy_reinvest_count5_remain_count']
        jango = DataFrame(jango_temp,
                          columns=jango_col_list,
                          index=jango_temp['id'])

        jango.loc[0, 'date'] = self.today
        jango.loc[0, 'today_profit'] = self.today_profit
        jango.loc[0, 'total_profit'] = self.total_profit
        jango.loc[0, 'total_invest'] = self.total_invest
        jango.loc[0, 'd2_deposit'] = self.d2_deposit
        jango.loc[0, 'today_purchase'] = self.change_total_purchase_price
        jango.loc[0, 'today_evaluation'] = self.change_total_eval_price
        jango.loc[0, 'today_invest'] = self.change_total_eval_profit_loss_price
        jango.loc[0, 'today_rate'] = float(self.change_total_earning_rate) / self.mod_gubun
        jango.loc[0, 'estimate_asset'] = self.change_estimated_deposit
        jango.loc[0, 'sell_point'] = self.sf.sell_point
        jango.loc[0, 'invest_limit_rate'] = self.sf.invest_limit_rate
        jango.loc[0, 'invest_unit'] = self.invest_unit
        jango.loc[0, 'limit_money'] = self.sf.limit_money

        if self.is_table_exist(self.open_api.db_name if hasattr(self, 'open_api') else self.db_name, "today_profit_list"):
            sql = "select sum(today_profit) from today_profit_list where today_profit >='%s' and date = '%s'"
            rows = self.engine_JB.execute(sql % (0, self.today)).fetchall()
            if rows[0][0] is not None:
                jango.loc[0, 'total_profitcut'] = int(rows[0][0])

            sql = "select sum(today_profit) from today_profit_list where today_profit < '%s' and date = '%s'"
            rows = self.engine_JB.execute(sql % (0, self.today)).fetchall()
            if rows[0][0] is not None:
                jango.loc[0, 'total_losscut'] = int(rows[0][0])

        sql = "select count(*) from (select code from all_item_db where sell_rate >='%s' and sell_date like '%s' group by code) temp"
        rows = self.engine_JB.execute(sql % (0, self.today + "%%")).fetchall()
        jango.loc[0, 'total_profitcut_count'] = int(rows[0][0])

        sql = "select count(*) from (select code from all_item_db where sell_rate < '%s' and sell_date like '%s' group by code) temp"
        rows = self.engine_JB.execute(sql % (0, self.today + "%%")).fetchall()
        jango.loc[0, 'total_losscut_count'] = int(rows[0][0])

        jango.to_sql('jango_data', self.engine_JB, if_exists='append')

        sql = "select date from jango_data"
        rows = self.engine_JB.execute(sql).fetchall()

        for i in range(len(rows)):
            sql = "update jango_data set today_earning_rate =round(today_profit / total_invest  * '%s',2) WHERE date='%s'"
            self.engine_JB.execute(sql % (100, rows[i][0]))

            sql = "UPDATE jango_data SET today_buy_count=(select count(*) from (select code from all_item_db where buy_date like '%s' group by code ) temp) WHERE date='%s'"
            self.engine_JB.execute(sql % (rows[i][0] + "%%", rows[i][0]))

            sql = "UPDATE jango_data SET today_buy_total_sell_count=(select count(*) from (select code from all_item_db a where buy_date like '%s' and (a.sell_date is not null or a.rate_std>='%s') group by code ) temp) WHERE date='%s'"
            self.engine_JB.execute(sql % (rows[i][0] + "%%", 0, rows[i][0]))

            sql = "UPDATE jango_data SET today_buy_total_possess_count=(select count(*) from (select code from all_item_db a where buy_date like '%s' and a.sell_date = '%s' group by code ) temp) WHERE date='%s'"
            self.engine_JB.execute(sql % (rows[i][0] + "%%", 0, rows[i][0]))

            sql = "UPDATE jango_data SET today_buy_today_profitcut_count=(select count(*) from (select code from all_item_db where buy_date like '%s' and sell_date like '%s' and (sell_rate >='%s' or rate_std>='%s'  ) group by code ) temp) WHERE date='%s'"
            self.engine_JB.execute(sql % (rows[i][0] + "%%", rows[i][0] + "%%", 0, 0, rows[i][0]))

            sql = "UPDATE jango_data SET today_buy_today_profitcut_rate=(select * from (select round(today_buy_today_profitcut_count /today_buy_count*100,2)  from jango_data WHERE date ='%s' limit 1) tmp)  WHERE date ='%s' limit 1"
            self.engine_JB.execute(sql % (rows[i][0], rows[i][0]))

            sql = "UPDATE jango_data SET today_buy_today_losscut_count=(select count(*) from (select code from all_item_db where buy_date like '%s' and sell_date like '%s' and sell_rate < '%s'  group by code ) tmp) WHERE date='%s' limit 1"
            self.engine_JB.execute(sql % (rows[i][0] + "%%", rows[i][0] + "%%", 0, rows[i][0]))

            sql = "UPDATE jango_data SET today_buy_today_losscut_rate=(select * from (select round(today_buy_today_losscut_count /today_buy_count *100,2)  from jango_data WHERE date ='%s' limit 1) tmp) WHERE date ='%s' limit 1"
            self.engine_JB.execute(sql % (rows[i][0], rows[i][0]))

            sql = "UPDATE jango_data SET today_buy_total_profitcut_count=(select count(*) from (select code from all_item_db where buy_date like '%s' and sell_rate >='%s'  group by code ) tmp) WHERE date='%s' limit 1"
            self.engine_JB.execute(sql % (rows[i][0] + "%%", 0, rows[i][0]))

            sql = "UPDATE jango_data SET today_buy_total_profitcut_rate=(select * from (select round(today_buy_total_profitcut_count /today_buy_count *100,2)  from jango_data WHERE date ='%s' limit 1) tmp) WHERE date ='%s' limit 1"
            self.engine_JB.execute(sql % (rows[i][0], rows[i][0]))

            sql = "UPDATE jango_data SET today_buy_total_losscut_count=(select count(*) from (select code from all_item_db where buy_date like '%s' and sell_rate < '%s'  group by code ) tmp) WHERE date='%s' limit 1"
            self.engine_JB.execute(sql % (rows[i][0] + "%%", 0, rows[i][0]))

            sql = "UPDATE jango_data SET today_buy_total_losscut_rate=(select * from (select round(today_buy_total_losscut_count/today_buy_count *100,2)  from jango_data WHERE date ='%s' limit 1) tmp) WHERE date ='%s' limit 1"
            self.engine_JB.execute(sql % (rows[i][0], rows[i][0]))

            sql = "UPDATE jango_data SET today_buy_reinvest_count0_sell_count=(select count(*) from (select code from all_item_db where buy_date like '%s' and sell_date is not null and reinvest_count=0 group by code ) tmp) WHERE date='%s'"
            self.engine_JB.execute(sql % (rows[i][0] + "%%", rows[i][0]))

            sql = "UPDATE jango_data SET today_buy_reinvest_count1_sell_count=(select count(*) from (select code from all_item_db where buy_date like '%s' and sell_date is not null and reinvest_count=1 group by code ) tmp) WHERE date='%s'"
            self.engine_JB.execute(sql % (rows[i][0] + "%%", rows[i][0]))

            sql = "UPDATE jango_data SET today_buy_reinvest_count2_sell_count=(select count(*) from (select code from all_item_db where buy_date like '%s' and sell_date is not null and reinvest_count=2 group by code ) tmp) WHERE date='%s'"
            self.engine_JB.execute(sql % (rows[i][0] + "%%", rows[i][0]))

            sql = "UPDATE jango_data SET today_buy_reinvest_count3_sell_count=(select count(*) from (select code from all_item_db where buy_date like '%s' and sell_date is not null and reinvest_count=3 group by code ) tmp) WHERE date='%s'"
            self.engine_JB.execute(sql % (rows[i][0] + "%%", rows[i][0]))

            sql = "UPDATE jango_data SET today_buy_reinvest_count4_sell_count=(select count(*) from (select code from all_item_db where buy_date like '%s' and sell_date is not null and reinvest_count=4 group by code ) tmp) WHERE date='%s'"
            self.engine_JB.execute(sql % (rows[i][0] + "%%", rows[i][0]))

            sql = "UPDATE jango_data SET today_buy_reinvest_count5_sell_count=(select count(*) from (select code from all_item_db where buy_date like '%s' and sell_date is not null and reinvest_count=5 group by code ) tmp) WHERE date='%s'"
            self.engine_JB.execute(sql % (rows[i][0] + "%%", rows[i][0]))

    def is_table_exist(self, db_name, table_name):
        sql = "select 1 from information_schema.tables where table_schema ='{}' and table_name = '{}'"
        rows = self.engine_craw.execute(sql.format(db_name, table_name)).fetchall()
        if len(rows) == 1:
            return True
        elif len(rows) == 0:
            return False

    # ──────────────────────────────────────────────
    #  체결 관련 (REST API - 제한적 지원)
    # ──────────────────────────────────────────────
    def chegyul_check(self):
        """체결 확인 (REST API - DB 기반 처리)"""
        logger.debug("chegyul_check 함수에 들어왔습니다!")
        # REST API에서는 실시간 체결 데이터가 없으므로 DB 기반으로 처리
        pass

    def final_chegyul_check(self):
        """최종 체결 확인 (REST API - DB 기반 처리)"""
        logger.debug("final_chegyul_check 함수에 들어왔습니다!")
        pass

    def chegyul_sync(self):
        """체결 동기화 (REST API - DB 기반 처리)"""
        pass

    def sell_final_check(self, code):
        """매도 최종 확인 (REST API - DB 기반 처리)"""
        logger.debug(f"sell_final_check: {code}")
        sql = "UPDATE all_item_db SET sell_date='%s', sell_rate='%s' WHERE code='%s' and sell_date = '%s' ORDER BY buy_date desc LIMIT 1"
        self.engine_JB.execute(sql % (self.today_detail, 0, code, 0))

    def stock_chegyul_check(self, code):
        """주식 체결 확인 (REST API - DB 기반 처리)"""
        sql = "select chegyul_check from all_item_db where code='%s' and sell_date = '%s' ORDER BY buy_date desc LIMIT 1"
        rows = self.engine_JB.execute(sql % (code, 0)).fetchall()
        if rows:
            return int(rows[0][0]) == 0
        return False

    def is_all_item_db_check(self, code):
        """all_item_db에 해당 종목이 있는지 확인"""
        sql = "select 1 from all_item_db where code='%s' and sell_date = '%s' LIMIT 1"
        rows = self.engine_JB.execute(sql % (code, 0)).fetchall()
        return len(rows) > 0

    def delete_all_item(self, code):
        sql = "DELETE FROM all_item_db WHERE code='%s'"
        self.engine_JB.execute(sql % (code,))

    def rate_check(self):
        """수익률 체크 (REST API - DB 기반 처리)"""
        logger.debug("rate_check 함수에 들어왔습니다!")
        pass

    def db_to_possesed_item(self):
        """보유 종목 DB 업데이트 (REST API)"""
        logger.debug("db_to_possesed_item 함수에 들어왔습니다!")
        self.check_balance()
        item_count = len(self.opw00018_output['multi'])
        possesed_item_temp = {'date': [], 'code': [], 'code_name': [], 'holding_amount': [], 'puchase_price': [],
                              'present_price': [], 'valuation_profit': [], 'rate': [], 'item_total_purchase': []}

        possesed_item = DataFrame(possesed_item_temp,
                                  columns=['date', 'code', 'code_name', 'holding_amount', 'puchase_price',
                                           'present_price', 'valuation_profit', 'rate', 'item_total_purchase'])

        for i in range(item_count):
            row = self.opw00018_output['multi'][i]
            possesed_item.loc[i, 'date'] = self.today
            possesed_item.loc[i, 'code'] = row[7]
            possesed_item.loc[i, 'code_name'] = row[0]
            possesed_item.loc[i, 'holding_amount'] = int(row[1])
            possesed_item.loc[i, 'puchase_price'] = int(row[2])
            possesed_item.loc[i, 'present_price'] = int(row[3])
            possesed_item.loc[i, 'valuation_profit'] = int(row[4])
            possesed_item.loc[i, 'rate'] = float(row[5])
            possesed_item.loc[i, 'item_total_purchase'] = int(row[6])

        possesed_item.to_sql('possessed_item', self.engine_JB, if_exists='replace')

    def buy_check(self):
        """매수 가능 여부 확인"""
        sql = "select today_buy_stop from setting_data limit 1"
        rows = self.engine_JB.execute(sql).fetchall()
        if rows[0][0] == str(0) or rows[0][0] == '0':
            return True
        else:
            return False

    def get_today_buy_list(self):
        """오늘 매수 리스트 가져오기"""
        logger.debug("get_today_buy_list 함수에 들어왔습니다!")
        # realtime_daily_buy_list에서 매수 대기 종목 조회
        sql = "select * from realtime_daily_buy_list where check_item = '0'"
        rows = self.engine_JB.execute(sql).fetchall()
        if rows:
            self.df_realtime_daily_buy_list = DataFrame(rows)
            self.len_df_realtime_daily_buy_list = len(rows)
        else:
            self.len_df_realtime_daily_buy_list = 0

    def basic_db_check(self, cursor):
        """기본 DB 체크 (open_api.py 와 동일)"""
        pass

    def _create_stock_info(self):
        """stock_info 테이블 생성 (collector_api에서 호출)"""
        pass

    def _create_stock_finance(self):
        """stock_finance 테이블 생성 (collector_api에서 호출)"""
        pass
    # ----------------------------------------------
    #  테마 정보 (REST API - 제한적 지원)
    # ----------------------------------------------
    def get_theme_info(self):
        logger.debug('get_theme_info')
        return {}

    # ----------------------------------------------
    #  KOA_Functions 특수함수 (REST API)
    # ----------------------------------------------
    def KOA_Functions(self, func_name, code):
        return self._koa_functions_rest(func_name, code)

    # ----------------------------------------------
    #  주식 재정 데이터 조회 (REST API)
    #  - ka10001 rate limit(유량=1) 대응: 호출 전 1초 대기 + 날짜별 shelve 캐시
    # ----------------------------------------------
    def get_stock_finance(self, code):
        logger.debug(f'get_stock_finance: {code}')
        today = datetime.datetime.now().strftime('%Y%m%d')
        cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ka10001_finance_cache.db')
        cache_path = os.path.abspath(cache_path)

        import shelve
        # 1) 같은 날짜에 이미 조회한 데이터는 캐시에서 재사용 (재실행/재시도 시 대폭 단축)
        try:
            with shelve.open(cache_path) as cache:
                key = f'{today}:{code}'
                if key in cache and cache[key]:
                    return cache[key]
        except Exception:
            pass

        try:
            # 2) rate limit 방지: 호출 전 1초 대기 (유량=1) + 429 시 재시도
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                try:
                    time.sleep(1.0)
                    self.set_input_value('종목코드', code)
                    self.comm_rq_data('opt10001_req', 'opt10001', 0, '0101')
                    break
                except RateLimitExceeded:
                    backoff = 1.0 * (2 ** (attempt - 1))
                    logger.warning(f'[WARN] ka10001 rate limit ({code}). 대기 {backoff}s 후 재시도 {attempt}/{max_retries}')
                    time.sleep(backoff)
                    if attempt == max_retries:
                        raise

            if hasattr(self, 'opt10001_output') and self.opt10001_output:
                result = self.opt10001_output
                self._log_finance_keys_once(result)
                try:
                    with shelve.open(cache_path) as cache:
                        cache[f'{today}:{code}'] = result
                except Exception:
                    pass
                return result

            # 3) 파싱 결과가 비어 있으면 원본 응답에서 직접 재추출
            if hasattr(self, '_tr_response') and self._tr_response:
                self._parse_opt10001(self._tr_response)
                if hasattr(self, 'opt10001_output') and self.opt10001_output:
                    result = self.opt10001_output
                    self._log_finance_keys_once(result)
                    try:
                        with shelve.open(cache_path) as cache:
                            cache[f'{today}:{code}'] = result
                    except Exception:
                        pass
                    return result
            return {}
        except Exception as e:
            logger.critical(f'get_stock_finance fail [{code}]: {e}')
            return {}
