#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
1. YouTube 批量下载器（视频 + 字幕）

- 输入：automated_video_workflow/1_youtube_downloader/input/url_list.txt（每行一个 URL）
- 输出：automated_video_workflow/1_youtube_downloader/output/downloads/ 下保存 mp4 与字幕（srt/vtt）
- 也支持命令行参数传入 --url 多个链接 或 --urls-file 文本文件

依赖：
  - yt-dlp
  - FFmpeg（可选，用于音视频合并/转码；若缺失将尽量下载单文件 MP4）

环境变量：
  - YT_PROXY：HTTP 代理地址，例如 http://127.0.0.1:7890

示例：
  python automated_video_workflow/1_youtube_downloader/batch_download.py --no-proxy \
    --output-dir automated_video_workflow/1_youtube_downloader/output/downloads
"""

import argparse
import os
from pathlib import Path
from typing import List, Optional

from yt_dlp import YoutubeDL

DEFAULT_INPUT_FILE = Path(__file__).resolve().parent / 'input' / 'url_list.txt'
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / 'output' / 'downloads'


def read_links(file_path: Path) -> List[str]:
    links: List[str] = []
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                links.append(line)
    return links


def ydl_opts(output_dir: Path, proxy: Optional[str], sub_langs: Optional[List[str]], all_subs: bool) -> dict:
    outtmpl = str(output_dir / '%(title)s-%(id)s.%(ext)s')
    # 尝试优先选择 mp4 容器；若需要合并会依赖 FFmpeg
    fmt = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
    opts = {
        'outtmpl': outtmpl,
        'format': fmt,
        'merge_output_format': 'mp4',
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitlesformat': 'srt/best',
        'noplaylist': True,
        'restrictfilenames': False,
        'nocheckcertificate': True,
        'quiet': False,
        'ignoreerrors': True,
    }
    if proxy:
        opts['proxy'] = proxy
    if all_subs:
        opts['subtitleslangs'] = 'all'
    elif sub_langs:
        opts['subtitleslangs'] = sub_langs
    return opts


def download(links: List[str], output_dir: Path, proxy: Optional[str], sub_langs: Optional[List[str]], all_subs: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    opts = ydl_opts(output_dir, proxy, sub_langs, all_subs)
    with YoutubeDL(opts) as ydl:
        for url in links:
            ydl.download([url])


def main() -> None:
    parser = argparse.ArgumentParser(description='YouTube 批量下载（视频 + 字幕）')
    parser.add_argument('--urls-file', type=str, default=str(DEFAULT_INPUT_FILE), help='包含链接的文本文件路径（每行一个链接）')
    parser.add_argument('--url', action='append', help='单个链接，可重复使用多个 --url 传多个链接')
    parser.add_argument('--output-dir', type=str, default=str(DEFAULT_OUTPUT_DIR), help='输出目录')
    parser.add_argument('--proxy', type=str, default=os.environ.get('YT_PROXY'), help='HTTP 代理，如 http://127.0.0.1:7890')
    parser.add_argument('--no-proxy', action='store_true', help='禁用代理')
    parser.add_argument('--sub-langs', type=str, default='en,zh-Hans,zh-Hant,zh-CN', help='字幕语言（逗号分隔），使用 --all-subs 下载全部')
    parser.add_argument('--all-subs', action='store_true', help='下载所有可用字幕语言')

    args = parser.parse_args()

    if args.no_proxy:
        proxy = None
    else:
        proxy = args.proxy

    links = []
    if args.url:
        links.extend(args.url)
    if args.urls_file:
        links.extend(read_links(Path(args.urls_file)))

    # 去重保持顺序
    seen = set()
    unique_links = []
    for u in links:
        if u not in seen:
            seen.add(u)
            unique_links.append(u)

    if not unique_links:
        print(f'未在 {args.urls_file} 中找到链接，也未传入 --url。')
        return

    sub_langs = [s.strip() for s in args.sub_langs.split(',') if s.strip()] if args.sub_langs else None
    download(unique_links, Path(args.output_dir), proxy, sub_langs, args.all_subs)
    print(f'完成，共处理 {len(unique_links)} 个链接，输出目录：{args.output_dir}')


if __name__ == '__main__':
    main()
