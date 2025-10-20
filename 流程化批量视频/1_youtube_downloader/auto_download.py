#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
1. YouTube 批量下载器（音频 + 缩略图）

- 输入：流程化批量视频/1_youtube_downloader/input/link_input.txt 中的链接（每行一个）
- 输出：流程化批量视频/1_youtube_downloader/output/downloads/ 下保存 mp3 与 jpg
- 也支持命令行参数传入 --url 多个链接 或 --urls-file 文本文件

依赖：
  - yt-dlp
  - python-docx（可选，若要扩展读取 docx）
  - FFmpeg（系统级依赖，用于音频转码）

环境变量：
  - YT_PROXY：HTTP 代理地址，例如 http://127.0.0.1:7890

示例：
  python 1_youtube_downloader/auto_download.py --no-proxy \
    --output-dir "流程化批量视频/1_youtube_downloader/output/downloads"
"""

import argparse
import os
from pathlib import Path
from typing import List, Optional

from yt_dlp import YoutubeDL

DEFAULT_INPUT_FILE = Path(__file__).resolve().parent / 'input' / 'link_input.txt'
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


def ydl_opts(output_dir: Path, proxy: Optional[str]) -> dict:
    outtmpl = str(output_dir / '%(title)s-%(id)s.%(ext)s')
    postprocessors = [
        {
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }
    ]
    opts = {
        'outtmpl': outtmpl,
        'writethumbnail': True,
        'postprocessors': postprocessors,
        'noplaylist': True,
        'restrictfilenames': False,
        'nocheckcertificate': True,
        'quiet': False,
        'ignoreerrors': True,
    }
    if proxy:
        opts['proxy'] = proxy
    return opts


def download(links: List[str], output_dir: Path, proxy: Optional[str]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    opts = ydl_opts(output_dir, proxy)
    with YoutubeDL(opts) as ydl:
        for url in links:
            ydl.download([url])


def main() -> None:
    parser = argparse.ArgumentParser(description='YouTube 批量下载（音频 + 缩略图）')
    parser.add_argument('--urls-file', type=str, default=str(DEFAULT_INPUT_FILE), help='包含链接的文本文件路径（每行一个链接）')
    parser.add_argument('--url', action='append', help='单个链接，可重复使用多个 --url 传多个链接')
    parser.add_argument('--output-dir', type=str, default=str(DEFAULT_OUTPUT_DIR), help='输出目录')
    parser.add_argument('--proxy', type=str, default=os.environ.get('YT_PROXY'), help='HTTP 代理，如 http://127.0.0.1:7890')
    parser.add_argument('--no-proxy', action='store_true', help='禁用代理')

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

    download(unique_links, Path(args.output_dir), proxy)
    print(f'完成，共处理 {len(unique_links)} 个链接，输出目录：{args.output_dir}')


if __name__ == '__main__':
    main()
