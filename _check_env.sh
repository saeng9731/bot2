#!/bin/bash
cd /home/opc/bot2
source /home/opc/new_autobot_env_py311/bin/activate
echo "=== Python 버전/비트 ==="
python -c "import sys; print('64bit:', sys.maxsize > 2**32)"
echo "=== tensorflow 확인 ==="
python -c "import tensorflow; print('tensorflow OK', tensorflow.__version__)" 2>&1 | tail -3
echo "=== ai/SPPModel import 확인 ==="
python -c "import ai.SPPModel" 2>&1 | tail -3
