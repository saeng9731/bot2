import pathlib

# 1. trader.py 수정
p = pathlib.Path(r'c:\Users\UserK\Desktop\bot2\trader.py')
content = p.read_text(encoding='utf-8')
content = content.replace('from library.open_api import *', 'from library.kiwoom_api import *')
content = content.replace('from PyQt5.QtWidgets import *', '')
content = content.replace('class Trader(QMainWindow):', 'class Trader:')
content = content.replace('super().__init__()', '')
content = content.replace('QTime.currentTime()', 'datetime.datetime.now()')
content = content.replace('QTime(9, 0, 0)', 'datetime.time(9, 0, 0)')
content = content.replace('QTime(15, 30, 0)', 'datetime.time(15, 30, 0)')
content = content.replace('QTime(9, 6, 0)', 'datetime.time(9, 6, 0)')
content = content.replace('if self.current_time > self.market_start_time and self.current_time < self.market_end_time:', 'if self.current_time.time() > self.market_start_time and self.current_time.time() < self.market_end_time:')
content = content.replace('if self.current_time < self.buy_end_time:', 'if self.current_time.time() < self.buy_end_time:')
content = content.replace('import sys', 'import sys\nimport datetime')
content = content.replace('app = QApplication(sys.argv)', '')
p.write_text(content, encoding='utf-8')
print('trader.py modified')

# 2. bot_stop.sh 생성
p2 = pathlib.Path(r'c:\Users\UserK\Desktop\bot2\sh\bot_stop.sh')
p2.write_text("""#!/bin/bash
# bot_stop.sh - Linux용 봇 중지 스크립트 (오라클 클라우드 서버용)
echo "bot_stop Start"
pkill -f "python.*simulator_v2.py" 2>/dev/null || true
pkill -f "python.*kind_crawling.py" 2>/dev/null || true
pkill -f "python.*ai_filter.py" 2>/dev/null || true
echo "봇이 중지되었습니다."
""", encoding='utf-8')
print('bot_stop.sh created')

# 3. delete_log.sh 생성
p3 = pathlib.Path(r'c:\Users\UserK\Desktop\bot2\sh\delete_log.sh')
p3.write_text("""#!/bin/bash
# delete_log.sh - Linux용 로그 삭제 스크립트 (오라클 클라우드 서버용)
echo "delete_log Start"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
find "$PROJECT_DIR/log" -name "jackbot.log*" -mtime +30 -delete 2>/dev/null || true
echo "30일 이상된 로그 파일이 삭제되었습니다."
""", encoding='utf-8')
print('delete_log.sh created')

print('All done!')