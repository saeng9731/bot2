import re

with open('/home/opc/bot2_dump_20260806.sql', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# daily_craw 섹션만 추출
m = re.search(r'-- Current Database: `daily_craw`', content)
if not m:
    print('daily_craw 섹션 없음')
    raise SystemExit
start = m.end()

# 다음 DB 시작 전까지가 daily_craw 섹션
m2 = re.search(r'-- Current Database: `min_craw`', content[start:])
end = start + m2.start() if m2 else len(content)
dc = content[start:end]

# 테이블별 INSERT 건수 세기
# INSERT INTO `테이블명` VALUES ... 패턴
tables = {}
for mm in re.finditer(r'INSERT INTO `([^`]+)` VALUES', dc):
    t = mm.group(1)
    tables[t] = tables.get(t, 0) + 1

print('daily_craw 테이블 수:', len(tables))

# 삼성전자 확인
if '삼성전자' in tables:
    print('삼성전자 INSERT 배치 수:', tables['삼성전자'])
# 각 INSERT가 여러 행 포함할 수 있으므로 행 수 확인
# 실제 행 수는 VALUES (..),(..) 패턴 개수로 계산

# 특정 테이블의 실제 행 수 추출
def count_rows(tbl_name):
    # 테이블 CREATE~UNLOCK 사이의 INSERT 문들에서 행 개수
    m = re.search(r'CREATE TABLE `' + re.escape(tbl_name) + r'`.*?UNLOCK TABLES;', dc, re.S)
    if not m:
        return None
    block = m.group(0)
    rows = 0
    for ins in re.finditer(r'INSERT INTO `[^`]+` VALUES\s*(.*?);', block, re.S):
        data = ins.group(1)
        # 단순 대략: '(..),(..)' 패턴 개수
        rows += len(re.findall(r'\),\(', data)) + 1
    return rows

for t in ['삼성전자', 'SK하이닉스', 'NAVER']:
    n = count_rows(t)
    print(f'{t}: {n}건' if n else f'{t}: 데이터 없음')

# 날짜 범위 확인 (삼성전자 첫/마지막 행 date)
m = re.search(r'CREATE TABLE `삼성전자`.*?UNLOCK TABLES;', dc, re.S)
if m:
    dates = re.findall(r"'(\d{8})'", m.group(0))
    if dates:
        print('삼성전자 날짜 범위:', min(dates), '~', max(dates))
