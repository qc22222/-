# 批量视频自动化工具集 - 快速测试指南

本仓库包含 5 个按流程分工的脚本，其中第 1 步是「从 YouTube 批量下载（音频 + 缩略图）」。

下面以第 1 步为例，说明如何在本地测试脚本是否能完成对应功能。


- 目录：`流程化批量视频 - 副本/1从youtube批量下载视频/auto_downloda.py`
- 功能：从 DOCX/文本/命令行读取 YouTube 链接，使用 yt-dlp 批量下载音频（mp3）和缩略图（jpg），并支持代理/浏览器 Cookies。

## 1. 环境准备

- Python 3.9+（推荐 3.10/3.11）
- 依赖安装：
  - `pip install -r requirements.txt`
  - 或者单独安装：`pip install yt-dlp python-docx`
- 系统需安装 FFmpeg：
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt-get update && sudo apt-get install -y ffmpeg`
  - Windows: 下载安装包 https://ffmpeg.org/ 并将 `ffmpeg` 加入 PATH
- 如需访问 YouTube，请确保网络可达。若使用代理，默认读取 `http://127.0.0.1:7890`，可通过参数或环境变量覆盖。

## 2. 最快测试方式（推荐）

无需准备 DOCX 文件，直接传入一个或多个链接：

- 单个链接：
  ```bash
  python "流程化批量视频 - 副本/1从youtube批量下载视频/auto_downloda.py" \
    --url "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --no-proxy
  ```
- 多个链接（重复 --url 参数）：
  ```bash
  python "流程化批量视频 - 副本/1从youtube批量下载视频/auto_downloda.py" \
    --url "https://youtu.be/xxxxxxxx" \
    --url "https://www.youtube.com/watch?v=yyyyyyyy" \
    --no-proxy
  ```
- 指定输出目录和代理：
  ```bash
  python "流程化批量视频 - 副本/1从youtube批量下载视频/auto_downloda.py" \
    --url "https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
    --out "~/Desktop/Youtube/YouTube下载" \
    --proxy "http://127.0.0.1:7890"
  ```

说明：
- 默认会将文件保存至 `~/Desktop/Youtube/YouTube下载` 目录。
- 无代理环境请加 `--no-proxy`；有代理则可使用 `--proxy` 指定地址，或设置环境变量 `YT_PROXY`。

## 3. 从 DOCX 批量读取并下载（符合生产流程）

1) 在本机创建并编辑：`~/Desktop/Youtube/youtube.docx`
   - 将要下载的 YouTube 链接每行一个粘贴进去（普通段落即可）。

2) 运行脚本：
   ```bash
   python "流程化批量视频 - 副本/1从youtube批量下载视频/auto_downloda.py"
   ```
   或者显式指定 DOCX 路径：
   ```bash
   python "流程化批量视频 - 副本/1从youtube批量下载视频/auto_downloda.py" \
     --docx "~/Desktop/Youtube/youtube.docx"
   ```

3) 下载结果：
   - 音频：`*.mp3`
   - 缩略图：`*.jpg`
   - 保存目录：`~/Desktop/Youtube/YouTube下载`（可用 `--out` 覆盖）

## 4. 也支持从文本文件读取

将链接写入一个纯文本文件（每行一个）：
```bash
python "流程化批量视频 - 副本/1从youtube批量下载视频/auto_downloda.py" --urls-file ./links.txt
```

## 5. 可选：使用浏览器 Cookies（处理地区/年龄限制等）

如部分视频需要登录/地区授权，可开启从浏览器读取 Cookies：
```bash
python "流程化批量视频 - 副本/1从youtube批量下载视频/auto_downloda.py" \
  --url "https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  --use-cookies --browser chrome
```
- 支持的浏览器示例：`chrome`、`brave`、`edge` 等。
- 首次使用可能需要系统已安装对应浏览器并可由 yt-dlp 读取其登录信息。

## 6. 常见问题排查

- 代理/网络问题：
  - 报错超时或 403/429，先用浏览器确认链接可打开，再检查 `--proxy` 设置或使用 `--no-proxy`。
- 没有生成 MP3：
  - 确认系统已安装 FFmpeg，并且 `ffmpeg` 在命令行可执行。
- Cookies 导入失败：
  - 不使用 `--use-cookies` 即可绕过；或检查浏览器、登录状态与权限。
- 路径含中文或空格：
  - 运行命令时最好用双引号括住脚本路径与目录。

## 7. 其它阶段脚本（简述）

- 2 伪原创自动化（TextRewriter）：`流程化批量视频 - 副本/2伪原创自动化/w_to_y.py`
- 3 出图自动化：`流程化批量视频 - 副本/3出图自动化/`
- 4 配音自动化：`流程化批量视频 - 副本/4配音自动化/`
- 5 剪辑自动化（CapCut 草稿注入）：`流程化批量视频 - 副本/5剪辑自动化/`

如需测试其他阶段，建议先阅读对应脚本顶部注释并准备所需 API 密钥/本地依赖，再按脚本的参数说明运行。
