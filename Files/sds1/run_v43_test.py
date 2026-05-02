#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SDS v4.3 测试运行脚本
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))
sys.path.insert(0, str(Path(__file__).parent))

from tests.test_task_generation_guard_v43 import run_tests

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
