import re

with open('/home/opc/bot2_dump_20260806.sql', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

# DB별 섹션 나누기
sections = re.split(r'-- Current Database: `([^`]+)`', content)
for i in range(1, len(sections), 2):
    db_name = sections[i]
    db_content = sections[i + 1]
    tables = re.findall(r'CREATE TABLE `([^`]+)`', db_content)
    date_tables = [t for t in tables if re.fullmatch(r'\d{8}', t)]
    print(f'{db_name}: 테이블 {len(tables)}개', end='')
    if date_tables:
        print(f'  (날짜 {len(date_tables)}개, 최신: {max(date_tables)})')
    else:
        print()
