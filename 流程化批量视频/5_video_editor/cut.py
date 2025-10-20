#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
5. 剪映草稿注入（安全占位实现）

- 自动查找图片：../3_image_generator/output/generated_images
- 自动查找音频/字幕：../4_audio_synthesizer/output/generated_audio
- 可通过 --draft-json 指定剪映草稿 draft_content.json 的路径

默认以“演练/干跑”模式运行（--dry-run）。它会列出将要注入的图片和音频/字幕数量，并给出
如何操作草稿文件的提示。后续可替换为对草稿 JSON 的真实编辑逻辑。

示例：
  python 5_video_editor/cut.py --draft-json ~/Desktop/JianyingPro Drafts/<id>/draft_content.json --apply
"""

import argparse
import json
import os
from glob import glob
from pathlib import Path
from typing import List

from dotenv import load_dotenv

DEFAULT_IMAGES_DIR = (Path(__file__).resolve().parents[1]
                      / '3_image_generator' / 'output' / 'generated_images')
DEFAULT_AUDIO_DIR = (Path(__file__).resolve().parents[1]
                     / '4_audio_synthesizer' / 'output' / 'generated_audio')


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
    # 尝试匹配常见目录（可根据个人安装位置调整）
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
    # 极简/安全：仅在 JSON 中添加一个元信息字段，不破坏剪映结构
    data = {}
    try:
        data = json.loads(draft_path.read_text(encoding='utf-8'))
    except Exception:
        print('警告：无法解析 JSON，跳过写入。')
        return

    if 'ctone_meta' not in data:
        data['ctone_meta'] = {}
    data['ctone_meta']['injected_by'] = 'cut.py'
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

    parser = argparse.ArgumentParser(description='剪映草稿注入（安全占位实现）')
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
