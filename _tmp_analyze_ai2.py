import re

with open('/tmp/simul_11_v2.log', 'r', encoding='utf-8', errors='ignore') as f:
    log = f.read()

analyzed = len(re.findall(r'(.+?) 종목 분석 중\.\.\.\.', log))
data_short = log.count('테스트 데이터가 적어서 realtime_daily_buy_list 에서 제외')
data_short2 = log.count('daily_craw 에')
not_match = log.count('기준에 부합하지 않으므로')
buy = log.count('매수')
sell = log.count('매도')

print(f'AI 분석 종목: {analyzed}')
print(f'데이터 부족 제외: {data_short}')
print(f'daily_craw 테이블 없음 제외: {data_short2}')
print(f'기준(ratio_cut) 미달 제외: {not_match}')
print(f'매수 발생: {buy}')
print(f'매도 발생: {sell}')

# 매수/매도 라인 샘플
print('\n=== 매수/매도 로그 샘플 ===')
for line in log.split('\n'):
    if '매수' in line or '매도' in line:
        print(line)
