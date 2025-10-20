#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
兼容旧路径的剪映脚本包装器

说明：原始脚本已迁移到模块化结构：
  流程化批量视频/5_video_editor/cut.py

本包装器将参数原样转发至新脚本，确保旧路径仍可用。
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    # 不解析参数，直接透传
    known, unknown = parser.parse_known_args()

    repo_root = Path(__file__).resolve().parents[1]
    new_script = repo_root.parent / '流程化批量视频' / '5_video_editor' / 'cut.py'

    if not new_script.exists():
        print('新脚本不存在，请确认仓库结构是否完整：', new_script)
        sys.exit(1)

    cmd = [sys.executable, str(new_script)] + unknown
    env = os.environ.copy()
    try:
        sys.exit(subprocess.call(cmd, env=env))
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == '__main__':
    main()
