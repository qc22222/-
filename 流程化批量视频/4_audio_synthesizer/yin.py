#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
4. 配音与字幕生成（占位实现）

- 自动读取：../2_text_rewriter/output/rewritten_texts/*.docx
- 输出：./output/generated_audio/
  - <docname>.mp3 或 <docname>.wav（若系统缺失 FFmpeg）
  - <docname>.srt

说明：
本脚本为占位实现，不调用外部 TTS 服务。它会：
  1) 解析每个文档的段落；
  2) 基于段落数量生成一段静音音频（每段 2 秒，可通过 --seconds-per-seg 调整）；
  3) 生成与之对应的 SRT 时间轴（每条字幕对应一个段落）。

后续可替换为 AzureTTS/MiniMax/Whisper 对齐等真实实现。

示例：
  python 4_audio_synthesizer/yin.py \
    --input-dir "流程化批量视频/2_text_rewriter/output/rewritten_texts" \
    --output-dir "流程化批量视频/4_audio_synthesizer/output/generated_audio"
"""

import argparse
from pathlib import Path
from typing import List

from docx import Document
from dotenv import load_dotenv
from pydub import AudioSegment

DEFAULT_INPUT_DIR = (Path(__file__).resolve().parents[1]
                     / '2_text_rewriter' / 'output' / 'rewritten_texts')
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / 'output' / 'generated_audio'


def list_docx_files(input_dir: Path) -> List[Path]:
    return sorted([p for p in input_dir.glob('*.docx') if p.is_file()])


def extract_paragraphs(docx_path: Path) -> List[str]:
    doc = Document(docx_path)
    items: List[str] = []
    for p in doc.paragraphs:
        t = (p.text or '').strip()
        if t:
            items.append(t)
    return items


def ms_to_srt(ts_ms: int) -> str:
    hours = ts_ms // 3600000
    ts_ms %= 3600000
    minutes = ts_ms // 60000
    ts_ms %= 60000
    seconds = ts_ms // 1000
    ms = ts_ms % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"


def write_srt(paras: List[str], seconds_per_seg: float, save_path: Path) -> None:
    lines = []
    cur_ms = 0
    dur_ms = int(seconds_per_seg * 1000)
    for i, text in enumerate(paras, start=1):
        start = ms_to_srt(cur_ms)
        end = ms_to_srt(cur_ms + dur_ms)
        lines.append(str(i))
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")
        cur_ms += dur_ms
    save_path.write_text("\n".join(lines), encoding='utf-8')


def synth_silent_audio(paras: List[str], seconds_per_seg: float) -> AudioSegment:
    seg_ms = int(seconds_per_seg * 1000)
    audio = AudioSegment.silent(duration=0)
    for _ in paras:
        audio += AudioSegment.silent(duration=seg_ms)
    return audio.set_frame_rate(48000).set_channels(1)


def process_doc(docx_path: Path, out_dir: Path, seconds_per_seg: float, prefer_mp3: bool) -> None:
    paras = extract_paragraphs(docx_path)
    if not paras:
        return
    out_dir.mkdir(parents=True, exist_ok=True)

    audio = synth_silent_audio(paras, seconds_per_seg)

    base = docx_path.stem
    audio_path_mp3 = out_dir / f"{base}.mp3"
    audio_path_wav = out_dir / f"{base}.wav"
    srt_path = out_dir / f"{base}.srt"

    exported = False
    if prefer_mp3:
        try:
            audio.export(audio_path_mp3, format='mp3')
            exported = True
            audio_out = audio_path_mp3
        except Exception:
            exported = False
    if not exported:
        # 回退到 WAV（无需 FFmpeg）
        audio.export(audio_path_wav, format='wav')
        audio_out = audio_path_wav

    write_srt(paras, seconds_per_seg, srt_path)
    print(f"{docx_path.name}: 生成音频 -> {audio_out.name}, 字幕 -> {srt_path.name}")


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description='配音与字幕生成（占位实现）')
    parser.add_argument('--input-dir', type=str, default=str(DEFAULT_INPUT_DIR), help='改写后文稿目录')
    parser.add_argument('--output-dir', type=str, default=str(DEFAULT_OUTPUT_DIR), help='音频与字幕输出目录')
    parser.add_argument('--seconds-per-seg', type=float, default=2.0, help='每段对应的音频时长（秒）')
    parser.add_argument('--mp3', action='store_true', help='尽量导出成 mp3（需要系统 FFmpeg）')

    args = parser.parse_args()

    in_dir = Path(args.input_dir)
    out_dir = Path(args.output_dir)

    in_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = list_docx_files(in_dir)
    if not files:
        print(f'未在 {in_dir} 找到 .docx 文稿')
        return

    for docx in files:
        process_doc(docx, out_dir, args.seconds_per_seg, prefer_mp3=args.mp3)

    print(f'完成，输出目录：{out_dir}')


if __name__ == '__main__':
    main()
