#!/bin/bash
cd /home/opc/bot2
source /home/opc/new_autobot_env_py311/bin/activate
python -c "import ast; ast.parse(open('library/kiwoom_api.py', encoding='utf-8').read()); print('문법 OK')"
