import os
import sys
import time
import random
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from docx import Document
import yt_dlp


def get_current_time() -> str:
    """获取当前时间的格式化字符串"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_message(message: str, level: str = "INFO") -> None:
    """打印带时间戳的日志"""
    print(f"[{get_current_time()}] [{level}] {message}")


def read_youtube_links() -> Optional[List[str]]:
    """
    从桌面 Youtube 文件夹中的 youtube.docx 读取视频链接。
    - 仅提取包含 youtube.com 或 youtu.be 的行
    """
    try:
        desktop_path = str(Path.home() / "Desktop")
        clips_folder = os.path.join(desktop_path, "Youtube")
        docx_path = os.path.join(clips_folder, "youtube.docx")

        if not os.path.exists(docx_path):
            log_message(f"文件不存在: {docx_path}", "ERROR")
            return None

        doc = Document(docx_path)
        links: List[str] = []

        for para in doc.paragraphs:
            text = (para.text or "").strip()
            if not text:
                continue
            if "youtube.com" in text or "youtu.be" in text:
                links.append(text)

        log_message(f"从文档中读取到 {len(links)} 个链接")
        return links

    except Exception as e:
        log_message(f"读取文件失败: {str(e)}", "ERROR")
        return None


def download_videos(links: List[str]) -> None:
    """下载 YouTube 视频（音频提取为 MP3，保存缩略图）"""
    if not links:
        log_message("没有找到要下载的链接", "WARNING")
        return

    # 创建下载目录在 Youtube/YouTube下载 下
    desktop_path = str(Path.home() / "Desktop")
    output_dir = os.path.join(desktop_path, "Youtube", "YouTube下载")
    os.makedirs(output_dir, exist_ok=True)

    # yt-dlp 配置
    ydl_opts: dict = {
        "format": "bestaudio/best",
        # 输出模板，音频与缩略图都放在 output_dir
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        # 后处理：抽取音频为 mp3 + 转换缩略图为 jpg
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
        "writethumbnail": True,
        # 使用 Chrome 浏览器 Cookies（如需）
        "cookiesfrombrowser": ("chrome",),
        # 网络与稳定性
        "proxy": "http://127.0.0.1:7890",
        "retries": 10,
        "fragment_retries": 10,
        "file_access_retries": 5,
        "retry_sleep": True,
        "sleep_interval": 3,
        "max_sleep_interval": 7,
        "sleep_interval_requests": 1,
        "socket_timeout": 30,
        "http_chunk_size": 10 * 1024 * 1024,  # 10MB
        # 地理位置绕过
        "geo_bypass": True,
        "geo_bypass_country": "US",
        # 请求头
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Origin": "https://www.youtube.com",
            "Referer": "https://www.youtube.com/",
            "Connection": "keep-alive",
        },
        # 输出日志
        "verbose": True,
        "no_warnings": False,
        # 解析
        "extract_flat": False,
        "noplaylist": False,
    }

    total = len(links)
    success = 0

    for i, url in enumerate(links, start=1):
        try:
            # 添加随机延时，避免被限制
            delay = random.uniform(2, 5)
            log_message(f"等待 {delay:.1f} 秒后开始下载...")
            time.sleep(delay)

            log_message(f"正在处理第 {i}/{total} 个视频...")
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


def main() -> None:
    """主函数"""
    try:
        log_message("开始运行 YouTube 下载程序")
        links = read_youtube_links()
        if links:
            log_message(f"成功读取 {len(links)} 个链接")
            download_videos(links)
        else:
            log_message("未能读取到任何链接", "ERROR")

    except KeyboardInterrupt:
        log_message("用户中断下载", "WARNING")
        sys.exit(1)
    except Exception as e:
        log_message(f"程序执行出错: {str(e)}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
