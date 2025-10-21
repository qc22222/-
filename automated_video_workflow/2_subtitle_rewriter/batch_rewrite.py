#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
2. 字幕改写（占位实现）

- 输入：automated_video_workflow/2_subtitle_rewriter/input/subtitles/ 下的 .srt/.vtt
- 输出：automated_video_workflow/2_subtitle_rewriter/output/rewritten_texts/ 下的 .txt

说明：
为便于端到端流程，本脚本提供一个无外部 API 的占位改写：
- 解析字幕内容，提取纯文本；
- 可选地为每一行添加前缀（如“改写：”），默认仅原样输出；
- 后续可在相同 CLI 基础上接入 Qwen/HuggingFace 等模型。

示例：
  python automated_video_workflow/2_subtitle_rewriter/batch_rewrite.py \
    --input-dir automated_video_workflow/2_subtitle_rewriter/input/subtitles \
    --output-dir automated_video_workflow/2_subtitle_rewriter/output/rewritten_texts \
    --prefix
"""

import argparse
import re
from pathlib import Path
from typing import Iterable, List

from dotenv import load_dotenv

DEFAULT_INPUT_DIR = Path(__file__).resolve().parent / 'input' / 'subtitles'
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / 'output' / 'rewritten_texts'


def read_lines(path: Path, encoding: str = 'utf-8') -> List[str]:
    try:
        return path.read_text(encoding=encoding).splitlines()
    except UnicodeDecodeError:
        return path.read_text(encoding='utf-8', errors='ignore').splitlines()


_time_re = re.compile(r"\d\d:\d\d:\d\d[,.]\d\d\d\s+--\>\s+\d\d:\d\d:\d\d[,.]\d\d\d")


def parse_subtitle_text(path: Path) -> List[str]:
    lines = read_lines(path)
    out: List[str] = []
    for ln in lines:
        s = ln.strip('\ufeff').strip()
        if not s:
            continue
        # SRT: numeric index lines
        if s.isdigit():
            continue
        # Timecode lines (SRT/VTT)
        if _time_re.search(s):
            continue
        # VTT header
        if s.upper().startswith('WEBVTT'):
            continue
        out.append(s)
    return out


def rewrite_lines(lines: Iterable[str], prefix: str | None = None) -> List[str]:
    out: List[str] = []
    for ln in lines:
        if prefix:
            out.append(f"{prefix}{ln}")
        else:
            out.append(ln)
    return out


def process_file(sub_path: Path, out_dir: Path, prefix: str | None) -> Path:
    texts = parse_subtitle_text(sub_path)
    if not texts:
        return out_dir / (sub_path.stem + '.txt')
    rewritten = rewrite_lines(texts, prefix=prefix)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / (sub_path.stem + '.txt')
    out_path.write_text("\n".join(rewritten), encoding='utf-8')
    return out_path


def list_subtitles(input_dir: Path) -> List[Path]:
    paths: List[Path] = []
    for ext in ('*.srt', '*.vtt'):
        paths.extend(sorted(input_dir.glob(ext)))
    return [p for p in paths if p.is_file()]


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description='字幕改写（占位实现）')
    parser.add_argument('--input-dir', type=str, default=str(DEFAULT_INPUT_DIR), help='字幕输入目录（SRT/VTT）')
    parser.add_argument('--output-dir', type=str, default=str(DEFAULT_OUTPUT_DIR), help='改写文本输出目录（TXT）')
    parser.add_argument('--prefix', action='store_true', help='是否为每行添加“改写：”前缀')

    args = parser.parse_args()

    in_dir = Path(args.input_dir)
    out_dir = Path(args.output_dir)
    in_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    subs = list_subtitles(in_dir)
    if not subs:
        print(f'未在 {in_dir} 找到字幕文件（.srt/.vtt）')
        return

    prefix = '改写：' if args.prefix else None
    count = 0
    for sub in subs:
        out_path = process_file(sub, out_dir, prefix)
        print(f'{sub.name} -> {out_path.name}')
        count += 1
    print(f'完成，处理 {count} 个字幕，输出目录：{out_dir}')


if __name__ == '__main__':
    main()
