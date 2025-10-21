#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Automated Video Workflow Orchestrator

一键编排运行 automated_video_workflow/ 下的五个阶段脚本。

默认按 1→2→3→4→5 顺序运行：
1) 批量下载 YouTube 视频与字幕
2) 批量改写字幕为文本
3) 文本分段生成占位图片
4) 文本合成占位音频与字幕
5) 剪映草稿占位注入（演练模式）

使用示例：
  python orchestrator.py
  python orchestrator.py --steps 1,2,3
  python orchestrator.py --skip 2 --apply-draft --draft-json "~/Desktop/.../draft_content.json"

说明：
- 本 orchestrator 仅串联目录与脚本，核心 AI/编辑逻辑由各阶段脚本决定；
- 可根据需要修改步骤间的“同步/拷贝”策略。
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent
WF = ROOT / 'automated_video_workflow'

# Step paths
STEP1 = WF / '1_youtube_downloader'
STEP2 = WF / '2_subtitle_rewriter'
STEP3 = WF / '3_segment_image_generator'
STEP4 = WF / '4_audio_generator'
STEP5 = WF / '5_video_synthesizer'

# Common IO
S1_URLS = STEP1 / 'input' / 'url_list.txt'
S1_OUT = STEP1 / 'output' / 'downloads'
S2_IN = STEP2 / 'input' / 'subtitles'
S2_OUT = STEP2 / 'output' / 'rewritten_texts'
S3_OUT = STEP3 / 'output' / 'generated_images'
S4_OUT = STEP4 / 'output' / 'generated_audio'


def run(argv: Iterable[str]) -> None:
    print('>>', ' '.join(map(str, argv)))
    subprocess.run(list(map(str, argv)), check=True)


def ensure_url_list() -> None:
    if not S1_URLS.exists():
        S1_URLS.parent.mkdir(parents=True, exist_ok=True)
        S1_URLS.write_text('# Put one YouTube URL per line.\n', encoding='utf-8')
        print(f'已创建占位 URL 列表：{S1_URLS}')


def sync_downloaded_subtitles() -> int:
    """将步骤1下载目录中的 .srt/.vtt 拷贝到步骤2输入目录。"""
    S2_IN.mkdir(parents=True, exist_ok=True)
    count = 0
    for ext in ('*.srt', '*.vtt'):
        for src in S1_OUT.glob(ext):
            dst = S2_IN / src.name
            try:
                shutil.copy2(src, dst)
                count += 1
            except Exception:
                pass
    print(f'同步字幕 {count} 个到 {S2_IN}')
    return count


def step1(proxy: str | None, no_proxy: bool, all_subs: bool, sub_langs: str | None) -> None:
    ensure_url_list()
    argv = [
        sys.executable, str(STEP1 / 'batch_download.py'),
        '--urls-file', str(S1_URLS),
        '--output-dir', str(S1_OUT),
    ]
    if no_proxy:
        argv.append('--no-proxy')
    elif proxy:
        argv += ['--proxy', proxy]
    if all_subs:
        argv.append('--all-subs')
    elif sub_langs:
        argv += ['--sub-langs', sub_langs]
    run(argv)


def step2(prefix: bool) -> None:
    sync_downloaded_subtitles()
    argv = [
        sys.executable, str(STEP2 / 'batch_rewrite.py'),
        '--input-dir', str(S2_IN),
        '--output-dir', str(S2_OUT),
    ]
    if prefix:
        argv.append('--prefix')
    run(argv)


def step3(input_dir: Path | None = None) -> None:
    in_dir = input_dir or S2_OUT
    argv = [
        sys.executable, str(STEP3 / 'batch_generate.py'),
        '--input-dir', str(in_dir),
        '--output-dir', str(S3_OUT),
    ]
    run(argv)


def step4(input_dir: Path | None = None, seconds_per_seg: float = 2.0, mp3: bool = False) -> None:
    in_dir = input_dir or S2_OUT
    argv = [
        sys.executable, str(STEP4 / 'batch_synthesize.py'),
        '--input-dir', str(in_dir),
        '--output-dir', str(S4_OUT),
        '--seconds-per-seg', str(seconds_per_seg),
    ]
    if mp3:
        argv.append('--mp3')
    run(argv)


def step5(images_dir: Path | None = None, audio_dir: Path | None = None, draft_json: str | None = None, apply: bool = False) -> None:
    images = images_dir or S3_OUT
    audio = audio_dir or S4_OUT
    argv = [
        sys.executable, str(STEP5 / 'json_editor.py'),
        '--images-dir', str(images),
        '--audio-dir', str(audio),
    ]
    if draft_json:
        argv += ['--draft-json', draft_json]
    if apply:
        argv.append('--apply')
    run(argv)


def parse_steps(steps: str | None, skip: str | None) -> list[int]:
    ordered = [1, 2, 3, 4, 5]
    if steps:
        sel: list[int] = []
        for token in steps.split(','):
            token = token.strip()
            if not token:
                continue
            if '-' in token:
                a, b = token.split('-', 1)
                try:
                    a, b = int(a), int(b)
                except ValueError:
                    continue
                if a <= b:
                    sel.extend(range(a, b + 1))
                else:
                    sel.extend(range(a, b - 1, -1))
            else:
                try:
                    sel.append(int(token))
                except ValueError:
                    pass
        ordered = [s for s in ordered if s in set(sel)]
    if skip:
        skipped = {int(x) for x in skip.split(',') if x.strip().isdigit()}
        ordered = [s for s in ordered if s not in skipped]
    return ordered


def main() -> None:
    ap = argparse.ArgumentParser(description='Automated Video Workflow Orchestrator')
    ap.add_argument('--steps', type=str, default=None, help='要运行的步骤，例如 "1,2,3" 或 "2-5"；默认 1-5')
    ap.add_argument('--skip', type=str, default=None, help='要跳过的步骤，例如 "2,5"')

    # step1 options
    ap.add_argument('--proxy', type=str, default=None, help='HTTP 代理，等同于步骤1的 --proxy')
    ap.add_argument('--no-proxy', action='store_true', help='禁用代理（步骤1）')
    ap.add_argument('--all-subs', action='store_true', help='下载所有字幕（步骤1）')
    ap.add_argument('--sub-langs', type=str, default='en,zh-Hans,zh-Hant,zh-CN', help='字幕语言列表（步骤1）')

    # step2 options
    ap.add_argument('--prefix', action='store_true', help='字幕改写时为每行加“改写：”前缀（步骤2）')

    # step4 options
    ap.add_argument('--seconds-per-seg', type=float, default=2.0, help='每段音频时长（步骤4）')
    ap.add_argument('--mp3', action='store_true', help='尽量导出 mp3（步骤4）')

    # step5 options
    ap.add_argument('--apply-draft', action='store_true', help='对草稿写入占位元信息（步骤5）')
    ap.add_argument('--draft-json', type=str, default=None, help='草稿 draft_content.json 路径（步骤5）')

    args = ap.parse_args()

    steps = parse_steps(args.steps, args.skip)
    print('将要执行的步骤：', steps)

    for s in steps:
        if s == 1:
            step1(args.proxy, args.no_proxy, args.all_subs, args.sub_langs)
        elif s == 2:
            step2(args.prefix)
        elif s == 3:
            step3()
        elif s == 4:
            step4(seconds_per_seg=args.seconds_per_seg, mp3=args.mp3)
        elif s == 5:
            step5(draft_json=args.draft_json, apply=args.apply_draft)

    print('全部步骤完成。输出目录：')
    print(' - 下载：', S1_OUT)
    print(' - 改写文本：', S2_OUT)
    print(' - 生成图片：', S3_OUT)
    print(' - 生成音频：', S4_OUT)


if __name__ == '__main__':
    main()
