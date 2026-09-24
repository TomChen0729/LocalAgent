import sys
from pathlib import Path

# 取得 LocalAgent 專案根目錄
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 將專案根目錄加入 Python import path
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
