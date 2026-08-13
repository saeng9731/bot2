# version 1.3.2
print("collector 프로그램이 시작 되었습니다!")

from library.collector_api import *
from library import cf

class Collector:
    print("collector 클래스에 들어왔습니다.")

    def __init__(self):
        print("__init__ 함수에 들어왔습니다.")
        self.collector_api = collector_api()

    def collecting(self):
        self.collector_api.code_update_check()

if __name__ == "__main__":
    print("__main__에 들어왔습니다.")
    # Linux(오라클 클라우드)에서는 QApplication 없이 실행
    if cf.IS_LINUX:
        c = Collector()
        c.collecting()
    else:
        # Windows에서는 기존 방식대로 QApplication 사용
        from PyQt5.QtWidgets import QApplication
        import sys
        app = QApplication(sys.argv)
        c = Collector()
        c.collecting()
