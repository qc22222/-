# 流程化批量视频（模块化重构）

本项目提供一套端到端的批量视频生产流水线，拆分为 5 个独立模块，每个模块都有清晰的输入/输出目录，并通过上一步的产物实现串联。目标是让流程更清晰、健壮、易于测试与维护。

注意：仓库中仍保留了旧版目录“流程化批量视频 - 副本”。为兼容旧路径，该目录下第 3/4/5 步脚本已改为包装器，会将参数透传到新目录的同名脚本。

## 一、目录结构

```
流程化批量视频/
├── 1_youtube_downloader/
│   ├── auto_download.py
│   ├── input/
│   │   └── link_input.txt      <-- 在此放入视频链接
│   └── output/
│       └── downloads/          <-- 下载的音频和封面存放于此
│
├── 2_text_rewriter/
│   ├── w_to_y.py
│   ├── input/
│   │   └── original_texts/     <-- 在此放入原始文案 .docx
│   └── output/
│       └── rewritten_texts/    <-- 改写后的文案存放于此
│
├── 3_image_generator/
│   ├── code.py
│   └── output/
│       └── generated_images/   <-- 生成的图片存放于此
│
├── 4_audio_synthesizer/
│   ├── yin.py
│   └── output/
│       └── generated_audio/    <-- 生成的配音和字幕存放于此
│
├── 5_video_editor/
│   └── cut.py                  <-- 安全占位实现，演练模式默认不写草稿
│
└── final_videos/               <-- 最终导出视频建议存放位置
```

## 二、端到端流程（更新后）

1) 下载：
- 将视频链接写入 1_youtube_downloader/input/link_input.txt（每行一个），或使用 `--url` 参数传入。
- 运行：
  ```bash
  python 流程化批量视频/1_youtube_downloader/auto_download.py --no-proxy
  ```
  文件输出至 1_youtube_downloader/output/downloads/。

2) 改写：
- 将原始文稿放入 2_text_rewriter/input/original_texts/。
- 运行：
  ```bash
  python 流程化批量视频/2_text_rewriter/w_to_y.py --prefix
  ```
  产物输出至 2_text_rewriter/output/rewritten_texts/。

3) 出图：
- 自动读取第 2 步的文稿，依据段落生成占位图片（可替换为真实出图 API）。
- 运行：
  ```bash
  python 流程化批量视频/3_image_generator/code.py
  ```
  图片输出至 3_image_generator/output/generated_images/。

4) 配音：
- 自动读取第 2 步的文稿，按段落生成静音音频与 SRT（占位实现，可替换为 TTS+对齐）。
- 运行：
  ```bash
  python 流程化批量视频/4_audio_synthesizer/yin.py --mp3
  ```
  输出至 4_audio_synthesizer/output/generated_audio/。

5) 剪辑：
- 自动查找第 3 步图片与第 4 步音频/字幕；
- 默认为“演练模式”仅打印计划，不修改草稿；如需写入占位元信息，添加 `--apply` 并通过 `--draft-json` 指定草稿路径。
- 运行：
  ```bash
  python 流程化批量视频/5_video_editor/cut.py --draft-json \
    "~/Desktop/Youtube/剪映draft/JianyingPro Drafts/<id>/draft_content.json" --apply
  ```

6) 导出：
- 打开剪映检查并导出最终视频，建议存放在项目根目录的 final_videos/ 下。

## 三、跨模块配置与密钥

- 建议在项目根目录创建 .env 管理密钥和配置（例如 GEMINI_API_KEY、代理地址等）。
- 本次重构的脚本均可无密钥运行（占位实现），便于 CI 与基本联调。后续可在相同 CLI 与目录结构基础上接入真实 API/模型。

## 四、命令行与参数（摘要）

- 1_youtube_downloader/auto_download.py
  - `--urls-file` 文本链接清单，默认 input/link_input.txt
  - `--url` 可重复传入多个链接
  - `--output-dir` 输出目录
  - `--proxy`/`--no-proxy` 代理设置（也可用环境变量 YT_PROXY）

- 2_text_rewriter/w_to_y.py
  - `--input-dir` 原始文稿目录
  - `--output-dir` 改写文稿目录
  - `--prefix` 是否在每段前加入“改写：”

- 3_image_generator/code.py
  - `--input-dir` 改写文稿目录
  - `--output-dir` 图片输出目录

- 4_audio_synthesizer/yin.py
  - `--input-dir` 改写文稿目录
  - `--output-dir` 音频/字幕目录
  - `--seconds-per-seg` 每段对应的时长（秒，默认 2.0）
  - `--mp3` 尝试导出 MP3（需要系统 FFmpeg）

- 5_video_editor/cut.py
  - `--images-dir` 图片目录
  - `--audio-dir` 音频/字幕目录
  - `--draft-json` 剪映草稿 draft_content.json 路径
  - `--apply` 真正写入占位元信息；默认为演练模式

## 五、依赖安装

- Python 3.9+
- 安装 Python 依赖：
  ```bash
  pip install -r requirements.txt
  ```
- 可选：系统安装 FFmpeg（建议，便于音频转码）。

## 六、后续计划

- 将占位逻辑替换为实际的 Gemini/Runware 出图、本地/云端 TTS、字幕对齐与剪映草稿注入。
- 继续完善 CLI 与日志，保证批量生产质量与稳定性。
