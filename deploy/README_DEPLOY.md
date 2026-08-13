# bot2(JackBot) 오라클 클라우드 ARM 서버 배포 가이드

KIS(한국투자증권, 모의투자) 봇이 이미 있는 서버에 **bot2(키움증권 봇)를 함께 설치**하는 절차입니다.

---

## 1단계. 서버 통합 (4대 → 1대)

> ⚠️ KIS는 모의투자 중이라 중지해도 금전 손실 없음. 그래도 주말 작업 권장.

### A. 나머지 3대 삭제 (오라클 콘솔)
1. OCI 콘솔 → **Compute → Instances**
2. 삭제할 인스턴스 3대 각각 **Terminate**
   - ⚠️ "부트 볼륨 보존" 체크 **해제** → 저장공간이 계정에 반환됨
3. **Storage → Block Volumes** 에 남은 볼륨이 있으면 모두 **삭제**
   - 그래야 남길 서버 1대에 디스크 200GB를 몰아줄 수 있음

### B. 남길 서버(mydeal3) 업그레이드
1. 인스턴스 **Stop**
2. **Edit → Resize**
   - CPU: **2 OCPU** / 메모리: **12GB** (Always Free 최대)
3. **부트 볼륨 확장**: 30GB → **최소 100GB, 여유로우면 200GB**
4. **Start**

> ⚠️ 항상 "Always Free" 표시 옵션만 선택. 초과 시 유료 청구됨.

---

## 2단계. bot2 코드 업로드 (FileZilla)

1. FileZilla → **SFTP 접속** (호스트: 서버IP, 포트 22, 사용자: opc)
2. `c:\Users\UserK\Desktop\bot2` 폴더 전체를 서버 **`/home/opc/bot2`** 로 업로드
3. 업로드 **제외 권장** (용량 절약):
   - `.git`, `__pycache__`, `kind_snapshots`, `KIND_xls`, `log`, `~`, `.vscode`

---

## 3단계. 설치 스크립트 실행 (MobaXterm)

```bash
cd /home/opc/bot2/deploy   # 업로드한 폴더에 deploy 폴더가 함께 있음
bash setup_bot2.sh
```

스크립트가 자동으로 하는 일:
1. **OS 자동 감지** (Oracle Linux = dnf, Ubuntu = apt) → MySQL 설치 + bot2 DB 4개 생성 (`daily_craw`, `min_craw`, `daily_buy_list`, `JackBot11_imi1`)
2. Miniconda(ARM64) 설치 + **`/home/opc/new_autobot_env_py311`** 경로에 Python 3.11 환경 생성
   - (이 경로는 `sh/*.sh`가 이미 참조하는 경로와 정확히 일치)
3. Python 패키지 설치 (ARM 호환, TensorFlow 제외)
4. `.env` 파일 생성 (DB 접속정보, 키움 API 키)
5. crontab에 bot2 스케줄 추가 (**기존 KIS 크론은 그대로 보존**, 크론에서 conda 환경 자동 활성화)

> AI 필터(tensorflow)도 설치하려면: `bash setup_bot2.sh --with-ai`

---

## 4단계. 동작 확인

```bash
# conda 환경 활성화 (또는 sh 스크립트와 동일한 경로 사용)
source /home/opc/new_autobot_env_py311/bin/activate

# DB 연결 테스트
cd /home/opc/bot2
python -c "from library import cf; print(cf.db_ip)"

# 콜렉터 1회 실행 (장마감 후에!)
python collector_v3.py

# 로그 확인
tail -f /home/opc/bot2/log/jackbot.log
```

---

## 5단계. 트레이더 실행 (장중)

```bash
# 장중에만 실행 (9:00~15:30)
source /home/opc/new_autobot_env_py311/bin/activate
cd /home/opc/bot2
nohup python trader.py >> log/trader.log 2>&1 &
```

> MobaXterm을 닫아도 계속 돌아가려면 `nohup ... &` 로 실행하세요.
> 종료: `pkill -f trader.py`

---

## ⚠️ 주의사항

| 항목 | 내용 |
|---|---|
| **장중 재부팅 금지** | KIS 모의봇 + bot2 둘 다 중단됨 |
| **KIS 크론 보존** | 통합 후 `crontab -l`로 KIS 항목이 그대로인지 확인 |
| **AI 학습은 장마감 후** | 2 OCPU를 TensorFlow가 점유하면 봇들이 느려짐 |
| **TensorFlow ARM 이슈** | `ai/SPPModel.py`의 `tensorflow.python.keras` import가 최신 TF에서 오류 가능 → ai_filter 사용 시 코드 수정 필요 |
| **크롬 크롤링** | ARM용 chromium 필요 (스크립트가 설치). chromedriver 버전 불일치 시 `kind_crawling.py`의 자동 설치 기능 사용 |

---

## 장애 시 복구

```bash
# crontab 백업 복원
crontab crontab_backup_YYYYMMDD.txt

# MySQL 상태 확인
sudo systemctl status mysql

# 로그 확인
tail -f /home/opc/bot2/log/jackbot.log
```
