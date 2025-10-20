import os
import sys
import time
import random
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import argparse

from docx import Document
import yt_dlp


def get_current_time() -> str:
    """获取当前时间的格式化字符串"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_message(message: str, level: str = "INFO") -> None:
    """打印带时间戳的日志"""
    print(f"[{get_current_time()}] [{level}] {message}")


def default_docx_path() -> str:
    desktop_path = str(Path.home() / "Desktop")
    clips_folder = os.path.join(desktop_path, "Youtube")
    return os.path.join(clips_folder, "youtube.docx")


def default_output_dir() -> str:
    desktop_path = str(Path.home() / "Desktop")
    return os.path.join(desktop_path, "Youtube", "YouTube下载")


def read_youtube_links(docx_path: Optional[str] = None) -> Optional[List[str]]:
    """从指定docx文件读取视频链接。如果未提供，则读取桌面 Youtube/youtube.docx"""
    try:
        path = docx_path or default_docx_path()
        if not os.path.exists(path):
            log_message(f"文件不存在: {path}", "ERROR")
            return None

        doc = Document(path)
        links: List[str] = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            if "youtube.com" in text or "youtu.be" in text:
                links.append(text)

        log_message(f"从文档中读取到 {len(links)} 个链接")
        return links
    except Exception as e:
        log_message(f"读取文件失败: {str(e)}", "ERROR")
        return None


def read_links_from_txt(txt_path: str) -> Optional[List[str]]:
    try:
        if not os.path.exists(txt_path):
            log_message(f"链接文件不存在: {txt_path}", "ERROR")
            return None
        with open(txt_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        links = [l for l in lines if ("youtube.com" in l or "youtu.be" in l)]
        log_message(f"从文本文件读取到 {len(links)} 个链接")
        return links
    except Exception as e:
        log_message(f"读取文本文件失败: {str(e)}", "ERROR")
        return None


def build_ydl_opts(output_dir: str,
                   proxy: Optional[str],
                   use_cookies: bool,
                   cookies_browser: Optional[str]) -> dict:
    """构建 yt-dlp 的配置"""
    ydl_opts: dict = {
        "format": "bestaudio/best",
        "paths": {"home": output_dir},
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            },
            {
                "key": "FFmpegThumbnailsConvertor",
                "format": "jpg",
            },
        ],
        "writethumbnail": True,  # 下载缩略图
        "outtmpl": {
            "default": "%(title)s.%(ext)s",
            "thumbnail": "%(title)s.%(ext)s",  # 缩略图文件名格式
        },
        "verbose": True,
        "no_warnings": False,
        "extract_flat": False,
        # 重试与错误处理
        "retries": 10,
        "fragment_retries": 10,
        "file_access_retries": 5,
        "retry_sleep": True,
        "sleep_interval": 3,
        "max_sleep_interval": 7,
        "sleep_interval_requests": 1,
        # 网络相关
        "socket_timeout": 30,
        "http_chunk_size": 10485760,  # 10MB
        "buffersize": 1024,
        # 地理位置绕过
        "geo_bypass": True,
        "geo_bypass_country": "US",
        # 请求头
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Origin": "https://www.youtube.com",
            "Referer": "https://www.youtube.com/",
            "Connection": "keep-alive",
        },
    }

    if proxy:
        ydl_opts["proxy"] = proxy

    if use_cookies and cookies_browser:
        # 仅在明确要求时使用浏览器Cookies，避免在CI或无浏览器环境报错
        ydl_opts["cookiesfrombrowser"] = (cookies_browser,)

    return ydl_opts


def download_videos(links: List[str],
                    output_dir: Optional[str] = None,
                    proxy: Optional[str] = None,
                    use_cookies: bool = False,
                    cookies_browser: Optional[str] = None) -> None:
    """下载 YouTube 视频（仅音频+缩略图）"""
    if not links:
        log_message("没有找到要下载的链接", "WARNING")
        return

    out_dir = output_dir or default_output_dir()
    os.makedirs(out_dir, exist_ok=True)

    ydl_opts = build_ydl_opts(out_dir, proxy, use_cookies, cookies_browser)

    total = len(links)
    success = 0

    for i, url in enumerate(links, 1):
        try:
            delay = random.uniform(2, 5)
            log_message(f"等待 {delay:.1f} 秒后开始下载...")
            time.sleep(delay)

            log_message(f"正在处理第 {i}/{total} 个视频: {url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                error_code = ydl.download([url])

            if error_code == 0:
                success += 1
                log_message(f"视频下载成功: {url}")
            else:
                log_message(f"视频下载失败: {url}", "ERROR")
        except Exception as e:
            log_message(f"下载失败: {str(e)}", "ERROR")
            log_message(f"跳过视频: {url}", "WARNING")

    log_message(f"下载完成! 成功: {success}/{total}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="从DOCX/文本/命令行读取YouTube链接并批量下载（音频+缩略图）"
    )
    parser.add_argument(
        "--docx", dest="docx", type=str, default=None,
        help="包含链接的DOCX文件路径（默认: ~/Desktop/Youtube/youtube.docx）",
    )
    parser.add_argument(
        "--urls-file", dest="urls_file", type=str, default=None,
        help="包含链接的纯文本文件路径（每行一个链接）",
    )
    parser.add_argument(
        "--url", dest="urls", action="append", default=None,
        help="直接通过参数传入单个链接，可重复传入多次",
    )
    parser.add_argument(
        "--out", dest="out", type=str, default=None,
        help="输出目录（默认: ~/Desktop/Youtube/YouTube下载）",
    )
    parser.add_argument(
        "--proxy", dest="proxy", type=str, default=os.environ.get("YT_PROXY", "http://127.0.0.1:7890"),
        help="HTTP代理地址，留空表示不使用代理（默认: 环境变量YT_PROXY或http://127.0.0.1:7890）",
    )
    parser.add_argument(
        "--no-proxy", dest="no_proxy", action="store_true",
        help="禁用代理",
    )
    parser.add_argument(
        "--use-cookies", dest="use_cookies", action="store_true",
        help="从浏览器读取Cookies（默认关闭，避免在无浏览器环境报错）",
    )
    parser.add_argument(
        "--browser", dest="browser", type=str, default=os.environ.get("YT_BROWSER", "chrome"),
        help="用于读取Cookies的浏览器（chrome、brave、edge等）",
    )
    return parser.parse_args()


def main():
    try:
        args = parse_args()
        log_message("开始运行YouTube下载程序")

        proxy = None if args.no_proxy else (args.proxy or None)

        # 链接来源优先级: --url(s) > --urls-file > --docx > 默认docx
        links: Optional[List[str]] = None
        if args.urls:
            links = [u.strip() for u in args.urls if u and u.strip()]
            log_message(f"从命令行参数收到 {len(links)} 个链接")
        elif args.urls_file:
            links = read_links_from_txt(args.urls_file)
        else:
            links = read_youtube_links(args.docx)

        if links:
            log_message(f"成功读取 {len(links)} 个链接")
            download_videos(
                links,
                output_dir=args.out,
                proxy=proxy,
                use_cookies=args.use_cookies,
                cookies_browser=args.browser,
            )
        else:
            log_message("未能读取到任何链接", "ERROR")
            sys.exit(1)
    except KeyboardInterrupt:
        log_message("用户中断下载", "WARNING")
        sys.exit(1)
    except Exception as e:
        log_message(f"程序执行出错: {str(e)}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
