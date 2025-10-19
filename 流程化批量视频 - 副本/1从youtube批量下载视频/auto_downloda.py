import os

import sys

import time

import random

from pathlib import Path

from datetime import datetime

from docx import Document

import yt_dlp

def get_current_time():
    """获取当前时间的格式化字符串"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log_message(message, level="INFO"):
    """打印带时间戳的日志"""
    print(f"[{get_current_time()}] [{level}] {message}")

def read_youtube_links():
    """从桌面剪辑文件夹中的youtube.docx读取视频链接"""
    try:
        # 获取桌面剪辑文件夹路径
        desktop_path = str(Path.home() / "Desktop")
        clips_folder = os.path.join(desktop_path, "Youtube")
        docx_path = os.path.join(clips_folder, "youtube.docx")

        if not os.path.exists(docx_path):
            log_message(f"文件不存在: {docx_path}", "ERROR")
            return None

        # 读取文档
        doc = Document(docx_path)
        links = []

        # 从每个段落中提取链接
        for para in doc.paragraphs:
            text = para.text.strip()
            if "youtube.com" in text or "youtu.be" in text:
                links.append(text)

        log_message(f"从文档中读取到 {len(links)} 个链接")
        return links

    except Exception as e:
        log_message(f"读取文件失败: {str(e)}", "ERROR")
        return None

def download_videos(links):
    """下载YouTube视频"""

if not links:

log\_message("没有找到要下载的链接", "WARNING")

return

# 创建下载目录在剪辑文件夹中

desktop\_path = str(Path.home() / "Desktop")

output\_dir = os.path.join(desktop\_path, "Youtube", "YouTube下载")

os.makedirs(output\_dir, exist\_ok=True)

# yt-dlp配置

ydl\_opts = {

'format': 'bestaudio/best',

'paths': {'home': output\_dir},

'postprocessors': \[{\
\
'key': 'FFmpegExtractAudio',\
\
'preferredcodec': 'mp3',\
\
'preferredquality': '192',\
\
}, {\
\
'key': 'FFmpegThumbnailsConvertor',\
\
'format': 'jpg'\
\
}\],

'writethumbnail': True, # 下载缩略图

'outtmpl': {

'default': '%(title)s.%(ext)s',

'thumbnail': '%(title)s.%(ext)s' # 缩略图文件名格式

},

'cookiesfrombrowser': ('chrome',),

'proxy': 'http://127.0.0.1:7890',

'verbose': True,

'no_warnings': False,
'extract_flat': False,
# 添加重试和错误处理选项
'retries': 10,
'fragment_retries': 10,
'file_access_retries': 5,
'retry_sleep': True,
'sleep_interval': 3,
'max_sleep_interval': 7,
'sleep_interval_requests': 1,
# 添加网络相关选项
'socket_timeout': 30,
'http_chunk_size': 10485760,  # 10MB
'buffersize': 1024,
# 添加地理位置绕过
'geo_bypass': True,
'geo_bypass_country': 'US',
# 添加请求头
'http_headers': {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate',
    'Origin': 'https://www.youtube.com',
    'Referer': 'https://www.youtube.com/',
    'Connection': 'keep-alive'
}
}

total = len(links)
success = 0

for i, url in enumerate(links, 1):
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

def main():
    """主函数"""
    try:
        log_message("开始运行YouTube下载程序")

        # 读取链接
        links = read_youtube_links()
        if links:
            log_message(f"成功读取 {len(links)} 个链接")
            # 下载视频
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
