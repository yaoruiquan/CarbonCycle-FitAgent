"""
Pytest configuration and fixtures.
Pytest 配置和测试夹具

Configures the Python path to allow importing from the app package.
配置 Python 路径以允许从 app 包导入
"""

import sys
from pathlib import Path

# Add project root to Python path
# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
