#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
5. 剪映草稿 JSON 处理（安全占位实现）

- 输入：
  - 图片目录：automated_video_workflow/5_video_synthesizer/input/images
  - 音频/字幕目录：automated_video_workflow/5_video_synthesizer/input/audio
- 输出：
  - 草稿目录：automated_video_workflow/5_video_synthesizer/output/drafts

说明：
默认运行在“演练模式”，仅统计可用的素材数量，并尝试定位常见位置的剪映草稿 draft_content.json；
如通过 --apply 与 --draft-json 指定草稿路径，则写入一个安全的占位元信息字段，不破坏草稿结构。
该脚本可在后续替换为对草稿 JSON 的真实注入与关键帧/转场等处理逻辑。

示例：
  python automated_video_workflow/5_video_synthesizer/json_editor.py --apply \
    --draft-json "~/Desktop/Youtube/剪映draft/JianyingPro Drafts/<id>/draft_content.json"
"""

import argparse
import json
import os
from glob import glob
from pathlib import Path
from typing import List

from dotenv import load_dotenv

DEFAULT_IMAGES_DIR = Path(__file__).resolve().parent / 'input' / 'images'
DEFAULT_AUDIO_DIR = Path(__file__).resolve().parent / 'input' / 'audio'


def list_images(images_dir: Path) -> List[Path]:
    exts = ('*.png', '*.jpg', '*.jpeg', '*.webp')
    paths: List[Path] = []
    for ptn in exts:
        paths.extend(sorted(images_dir.glob(ptn)))
    return [p for p in paths if p.is_file()]


def list_audio(audio_dir: Path) -> List[Path]:
    exts = ('*.mp3', '*.wav', '*.m4a')
    paths: List[Path] = []
    for ptn in exts:
        paths.extend(sorted(audio_dir.glob(ptn)))
    return [p for p in paths if p.is_file()]


def list_srt(audio_dir: Path) -> List[Path]:
    return sorted([p for p in audio_dir.glob('*.srt') if p.is_file()])


def find_latest_draft_on_desktop() -> Path | None:
    candidates = [
        os.path.expanduser('~/Desktop/Youtube/剪映draft/JianyingPro Drafts/*/draft_content.json'),
        os.path.expanduser('~/Documents/JianyingPro Drafts/*/draft_content.json'),
        os.path.expanduser('~/Movies/JianyingPro Drafts/*/draft_content.json'),
    ]
    found: List[str] = []
    for pattern in candidates:
        found.extend(glob(pattern))
    if not found:
        return None
    latest = max(found, key=os.path.getmtime)
    return Path(latest)


def apply_stub_changes(draft_path: Path, images: List[Path], audios: List[Path]) -> None:
    data = {}
    try:
        data = json.loads(draft_path.read_text(encoding='utf-8'))
    except Exception:
        print('警告：无法解析 JSON，跳过写入。')
        return

    if 'ctone_meta' not in data:
        data['ctone_meta'] = {}
    data['ctone_meta']['injected_by'] = 'json_editor.py'
    data['ctone_meta']['images_count'] = len(images)
    data['ctone_meta']['audios_count'] = len(audios)

    backup = draft_path.with_suffix('.json.bak')
    try:
        if not backup.exists():
            backup.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        draft_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'已写入占位元信息，并生成备份：{backup}')
    except Exception as e:
        print(f'写入失败：{e}')


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description='剪映草稿 JSON 处理（安全占位实现）')
    parser.add_argument('--images-dir', type=str, default=str(DEFAULT_IMAGES_DIR), help='图片目录')
    parser.add_argument('--audio-dir', type=str, default=str(DEFAULT_AUDIO_DIR), help='音频/字幕目录')
    parser.add_argument('--draft-json', type=str, default=None, help='剪映草稿 draft_content.json 路径')
    parser.add_argument('--apply', action='store_true', help='对草稿写入占位元信息（默认仅演练）')

    args = parser.parse_args()

    images_dir = Path(args.images_dir)
    audio_dir = Path(args.audio_dir)

    images = list_images(images_dir)
    audios = list_audio(audio_dir)
    srts = list_srt(audio_dir)

    print(f'发现图片 {len(images)} 张，音频 {len(audios)} 个，字幕 {len(srts)} 个。')

    draft_path = Path(args.draft_json) if args.draft_json else find_latest_draft_on_desktop()
    if draft_path and draft_path.exists():
        print(f'检测到草稿文件：{draft_path}')
        if args.apply:
            apply_stub_changes(draft_path, images, audios)
        else:
            print('当前为演练模式：未对草稿进行写入。如需写入请添加 --apply')
    else:
        print('未找到有效的草稿文件。请通过 --draft-json 指定准确路径。')


if __name__ == '__main__':
    main()
