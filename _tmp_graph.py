import matplotlib
matplotlib.use('Agg')  # 서버(헤드리스)용
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pymysql
import sys
from datetime import datetime
sys.path.insert(0, '/home/opc/bot2')
from library import cf

# matplotlib 한글 폰트 설정
from matplotlib import font_manager
import os
font_dirs = ['/usr/share/fonts', '/usr/local/share/fonts', os.path.expanduser('~/.fonts')]
avail = []
for d in font_dirs:
    if os.path.isdir(d):
        for root, dirs, files in os.walk(d):
            for f in files:
                if f.lower().endswith(('.ttf', '.otf', '.ttc')):
                    avail.append(os.path.join(root, f))
font_added = False
for f in avail:
    try:
        font_manager.fontManager.addfont(f)
        name = font_manager.FontProperties(fname=f).get_name()
        if any(k in name for k in ['Nanum', 'Malgun', 'Apple', 'Noto', 'Ko', 'Gulim', 'Batang']):
            plt.rcParams['font.family'] = name
            font_added = True
            print('한글 폰트 사용:', name)
            break
    except Exception:
        pass
if not font_added:
    print('[경고] 한글 폰트 없음 - 한국어가 깨질 수 있음')

plt.rcParams['axes.unicode_minus'] = False

con = pymysql.connect(host=cf.db_ip, port=int(cf.db_port), user=cf.db_id, password=cf.db_passwd, db=cf.imi1_db_name, charset='utf8mb4')
cur = con.cursor()

# 시뮬레이션별 데이터: 시뮬레이터마다 별도 DB에 있을 수 있음. 일단 jango_data에서 조회
cur.execute("show columns from jango_data")
cols = [r[0] for r in cur.fetchall()]

# 조회할 컬럼
sel = []
for c in ['date', 'total_asset', 'today_profit', 'total_profit', 'total_invest', 'd2_deposit']:
    if c in cols:
        sel.append(c)
print('조회 컬럼:', sel)

cur.execute("select {} from jango_data order by date".format(','.join(sel)))
rows = cur.fetchall()
print('데이터 행 수:', len(rows))
if not rows:
    print('그래프를 그릴 데이터가 없습니다. 시뮬레이션 완료 후 다시 실행하세요.')
    con.close()
    sys.exit(0)

# 데이터 변환
dates = []
data = {c: [] for c in sel if c != 'date'}
for r in rows:
    rd = dict(zip(sel, r))
    try:
        d = datetime.strptime(str(rd['date'])[:8], '%Y%m%d')
        dates.append(d)
        for c in data:
            v = rd[c]
            try:
                data[c].append(float(v) if v is not None else None)
            except (ValueError, TypeError):
                data[c].append(None)
    except Exception:
        continue

# 그래프
fig, axes = plt.subplots(len(data), 1, figsize=(12, 3.5 * len(data)), sharex=True)
if len(data) == 1:
    axes = [axes]

for ax, (col, vals) in zip(axes, data.items()):
    ax.plot(dates, vals, marker='o', markersize=2, linewidth=1, label=col)
    ax.set_ylabel(col)
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)

axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
axes[-1].xaxis.set_major_locator(mdates.MonthLocator())
plt.xticks(rotation=45)
plt.tight_layout()
out = '/home/opc/bot2/simul_graph.png'
plt.savefig(out, dpi=100)
print('그래프 저장:', out)

# 요약 출력
print('\n=== 최근 5일 요약 ===')
for i in range(max(0, len(rows) - 5), len(rows)):
    r = dict(zip(sel, rows[i]))
    print(r)

con.close()
