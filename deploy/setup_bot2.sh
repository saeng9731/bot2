#!/bin/bash
# ============================================================
#  bot2(JackBot) Oracle Cloud ARM 서버 설치 스크립트
#  - KIS(한국투자증권) 봇과 함께 쓰는 서버 기준 (KIS는 건드리지 않음)
#  - 사전 준비: FileZilla로 bot2 폴더를 /home/opc/bot2 에 업로드
#  - 실행 방법: bash setup_bot2.sh
# ============================================================

set -e

PROJECT_DIR="/home/opc/bot2"
CONDA_BASE="/home/opc/miniconda3"
ENV_NAME="new_autobot_env_py311"

# 사용자가 설정할 DB 비밀번호 (기본값은 cf.py와 동일)
DB_ID="bot"
DB_PASSWD="${DB_PASSWD:-nastar79}"

# 패키지 매니저 감지 (Oracle Linux = dnf, Ubuntu = apt)
if command -v dnf >/dev/null 2>&1; then
    PKG_INSTALL="sudo dnf install -y"
elif command -v yum >/dev/null 2>&1; then
    PKG_INSTALL="sudo yum install -y"
else
    PKG_INSTALL="sudo apt install -y"
fi

echo "========================================================"
echo " bot2 설치 시작"
echo " 프로젝트: $PROJECT_DIR"
echo " conda 환경: /home/opc/new_autobot_env_py311"
echo " 패키지 매니저: ${PKG_INSTALL}"
echo "========================================================"

# ── 0) bot2 코드 존재 확인 ─────────────────────────────────
if [ ! -f "$PROJECT_DIR/collector_v3.py" ]; then
    echo "[오류] $PROJECT_DIR 에 bot2 코드가 없습니다."
    echo "       FileZilla(SFTP)로 먼저 업로드 한 뒤 다시 실행하세요."
    exit 1
fi

echo ""
echo "=== [1/6] 시스템 패키지 설치 (MySQL, Chromium) ==="
if command -v dnf >/dev/null 2>&1; then
    # Oracle Linux
    sudo dnf update -y || true
    sudo dnf install -y mysql-server curl wget || true
    sudo dnf install -y chromium chromium-headless 2>/dev/null || true
    # 오라클 리눅스 기본 리포지토리에 chromium이 없을 수 있음 - 실패해도 진행
elif command -v apt >/dev/null 2>&1; then
    # Ubuntu
    sudo apt update -y
    sudo apt install -y mysql-server curl wget || true
    sudo apt install -y chromium-browser 2>/dev/null || true
else
    echo "[경고] 알 수 없는 OS - 패키지 설치는 수동으로 진행하세요"
fi

echo ""
echo "=== [2/6] MySQL 시작 및 bot2 전용 DB 생성 ==="
# Oracle Linux는 서비스명이 'mysqld', Ubuntu는 'mysql' - 둘 다 시도
sudo systemctl enable mysql 2>/dev/null || sudo systemctl enable mysqld 2>/dev/null || true
sudo systemctl start mysql 2>/dev/null || sudo systemctl start mysqld 2>/dev/null || sudo service mysql start || true

# 시작 확인 (최대 30초 대기)
for i in $(seq 1 15); do
    if sudo mysqladmin ping >/dev/null 2>&1; then
        echo "MySQL 정상 동작 중 ✅"
        break
    fi
    sleep 2
done

sudo mysql -e "CREATE DATABASE IF NOT EXISTS daily_craw CHARACTER SET utf8mb4;"
sudo mysql -e "CREATE DATABASE IF NOT EXISTS min_craw CHARACTER SET utf8mb4;"
sudo mysql -e "CREATE DATABASE IF NOT EXISTS daily_buy_list CHARACTER SET utf8mb4;"
sudo mysql -e "CREATE DATABASE IF NOT EXISTS JackBot${IMI1_SIMUL_NUM:-11}_imi1 CHARACTER SET utf8mb4;"

sudo mysql -e "CREATE USER IF NOT EXISTS '${DB_ID}'@'localhost' IDENTIFIED BY '${DB_PASSWD}';"
sudo mysql -e "GRANT ALL PRIVILEGES ON *.* TO '${DB_ID}'@'localhost';"
sudo mysql -e "FLUSH PRIVILEGES;"
echo "MySQL DB 생성 완료 (KIS DB는 건드리지 않았습니다)"

echo ""
echo "=== [3/6] Miniconda(ARM64) 설치 및 Python 환경 생성 ==="
if [ ! -d "$CONDA_BASE" ]; then
    cd /tmp
    # curl 우선, 없으면 wget 사용
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh -o miniconda.sh
    else
        wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh -O miniconda.sh
    fi
    bash miniconda.sh -b -p "$CONDA_BASE"
    echo "Miniconda 설치 완료"
else
    echo "Miniconda 이미 설치됨"
fi

# conda 초기화 (현재 셸에서 사용 가능하게)
source "$CONDA_BASE/etc/profile.d/conda.sh"

# Anaconda 채널 이용약관 동의 (신규 Miniconda 필수)
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main 2>/dev/null || true
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r 2>/dev/null || true

# bot2 sh 스크립트가 참조하는 경로(/home/opc/new_autobot_env_py311)에 정확히 생성
ENV_PATH="/home/opc/new_autobot_env_py311"
if [ ! -d "$ENV_PATH" ]; then
    conda create -p "$ENV_PATH" python=3.11 -y
    echo "$ENV_PATH 환경 생성 완료"
else
    echo "$ENV_PATH 환경 이미 존재"
fi

# 신형 conda는 env/bin/activate 파일을 만들지 않을 수 있어 직접 생성
if [ ! -f "$ENV_PATH/bin/activate" ]; then
    printf '#!/bin/bash\nexport PATH="%s/bin:$PATH"\nexport CONDA_PREFIX="%s"\nexport CONDA_DEFAULT_ENV="%s"\n' "$ENV_PATH" "$ENV_PATH" "new_autobot_env_py311" > "$ENV_PATH/bin/activate"
    chmod +x "$ENV_PATH/bin/activate"
    echo "activate 파일 생성 완료"
fi

echo ""
echo "=== [4/6] Python 패키지 설치 (ARM 호환) ==="
conda activate "$ENV_PATH"

pip install --upgrade pip
pip install \
    requests \
    pymysql \
    "sqlalchemy==1.4.54" \
    "pandas==2.0.3" \
    "numpy==1.26.4" \
    lxml \
    selenium \
    chromedriver-autoinstaller \
    dart_fss \
    cryptography \
    matplotlib \
    scikit-learn

echo "코어 패키지 설치 완료"

# AI 필터(TensorFlow)는 ARM 이슈가 있어 옵션으로 분리
# 사용법: bash setup_bot2.sh --with-ai
if [ "$1" == "--with-ai" ]; then
    echo "TensorFlow(ARM용 tensorflow-cpu) 설치 중... (시간이 오래 걸립니다)"
    pip install tensorflow-cpu
    echo "TensorFlow 설치 완료 (ai_filter 사용 전 ARM 호환 코드 확인 필요)"
else
    echo "[안내] ai_filter(TensorFlow)는 설치하지 않았습니다."
    echo "       필요시 나중에: conda activate /home/opc/new_autobot_env_py311 && pip install tensorflow-cpu"
fi

echo ""
echo "=== [5/6] .env 파일 생성 (없을 때만) ==="
if [ -f "$PROJECT_DIR/.env" ]; then
    echo ".env 이미 존재 - 내용을 확인하세요"
else
    cat > "$PROJECT_DIR/.env" <<EOF
DB_ID=$DB_ID
DB_PASSWD=$DB_PASSWD
DB_IP=localhost
DB_PORT=3306
IMI1_ACCOUNT=8128743211
IMI1_SIMUL_NUM=11
START_DAILY_BUY_LIST=20250804
KIWOOM_API_KEY=QdDdAw4X_7uf4zIdDKuHV-Dkqxv1MsLvPBc7aQzKrdk
KIWOOM_API_SECRET=FgEBNFri25s6hqtwXIg067pg8TkPGo2mzfaVa_tSeYA
KIWOOM_IS_MOCK=True
USE_ETF=False
MAX_API_CALL=99999
EOF
    echo ".env 생성 완료: $PROJECT_DIR/.env"
fi

echo ""
echo "=== [6/6] crontab 등록 (기존 KIS 크론은 보존) ==="
# 기존 크론 백업
crontab -l > /home/opc/crontab_backup_$(date +%Y%m%d).txt 2>/dev/null || true

# bot2 항목이 이미 있는지 확인 후 추가
if ! crontab -l 2>/dev/null | grep -q "bot2"; then
    ( crontab -l 2>/dev/null; cat <<'CRONEOF'

# ===== bot2 (JackBot - 키움증권) =====
# SHELL을 bash로 지정 (source 사용 가능하게)
SHELL=/bin/bash
# 매일 장마감 후 데이터 수집 (한국투자증권 봇과 시간대 안 겹침)
# 주의! 서버 시간대가 UTC 이므로 한국시간 15:30 = UTC 06:30 로 환산해서 등록
30 6 * * 1-5 cd /home/opc/bot2 && source /home/opc/new_autobot_env_py311/bin/activate && bash sh/collector.sh >> /home/opc/bot2/log/collector_cron.log 2>&1
# 주말 하루 한번 AI 필터 (선택, tensorflow 설치 후)
# 30 15 * * 6 cd /home/opc/bot2 && source /home/opc/new_autobot_env_py311/bin/activate && bash sh/ai_filter.sh JackBot11_imi1 11 >> /home/opc/bot2/log/ai_cron.log 2>&1
CRONEOF
    ) | crontab -
    echo "crontab에 bot2 스케줄 추가 완료"
else
    echo "bot2 crontab 이미 존재"
fi

echo ""
echo "========================================================"
echo " 설치 완료!"
echo ""
echo " 다음 단계 (MobaXterm에서 실행):"
echo "  1) 환경 테스트:"
echo "     source /home/opc/miniconda3/etc/profile.d/conda.sh"
echo "     conda activate /home/opc/new_autobot_env_py311"
echo "     cd /home/opc/bot2"
echo "     python -c \"from library import cf; print(cf.db_ip)\""
echo ""
echo "  2) 콜렉터 테스트:  conda activate /home/opc/new_autobot_env_py311 && cd /home/opc/bot2 && python collector_v3.py"
echo "  3) 로그 확인:       tail -f /home/opc/bot2/log/jackbot.log"
echo ""
echo " [중요] 장중(9:00~15:30)에는 테스트 실행을 피하세요."
echo "========================================================"

