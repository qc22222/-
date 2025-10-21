#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
4. 文本转音频与字幕（占位实现）

- 输入：automated_video_workflow/4_audio_generator/input/texts/ 下的 .txt（或通过 --input-dir 指定）
- 输出：automated_video_workflow/4_audio_generator/output/generated_audio/ 下的音频与 SRT

说明：
为每个文本文件的每一行生成一段静音音频（默认 2 秒），并生成对应的 SRT 时间轴。
后续可替换为 Index-TTS/AzureTTS/MiniMax+Whisper 对齐等真实实现。

示例：
  python automated_video_workflow/4_audio_generator/batch_synthesize.py \
    --input-dir automated_video_workflow/2_subtitle_rewriter/output/rewritten_texts \
    --output-dir automated_video_workflow/4_audio_generator/output/generated_audio \
    --mp3
"""

import argparse
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from pydub import AudioSegment

DEFAULT_INPUT_DIR = Path(__file__).resolve().parent / 'input' / 'texts'
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / 'output' / 'generated_audio'


def read_nonempty_lines(path: Path) -> List[str]:
    lines = path.read_text(encoding='utf-8', errors='ignore').splitlines()
    return [ln.strip() for ln in lines if ln.strip()]


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


def process_text(txt_path: Path, out_dir: Path, seconds_per_seg: float, prefer_mp3: bool) -> None:
    paras = read_nonempty_lines(txt_path)
    if not paras:
        return
    out_dir.mkdir(parents=True, exist_ok=True)

    audio = synth_silent_audio(paras, seconds_per_seg)

    base = txt_path.stem
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
        audio.export(audio_path_wav, format='wav')
        audio_out = audio_path_wav

    write_srt(paras, seconds_per_seg, srt_path)
    print(f"{txt_path.name}: 生成音频 -> {audio_out.name}, 字幕 -> {srt_path.name}")


def list_texts(input_dir: Path) -> List[Path]:
    return sorted([p for p in input_dir.glob('*.txt') if p.is_file()])


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description='文本转音频与字幕（占位实现）')
    parser.add_argument('--input-dir', type=str, default=str(DEFAULT_INPUT_DIR), help='改写文本目录（TXT）')
    parser.add_argument('--output-dir', type=str, default=str(DEFAULT_OUTPUT_DIR), help='音频与字幕输出目录')
    parser.add_argument('--seconds-per-seg', type=float, default=2.0, help='每段对应的音频时长（秒）')
    parser.add_argument('--mp3', action='store_true', help='尽量导出成 mp3（需要系统 FFmpeg）')

    args = parser.parse_args()

    in_dir = Path(args.input_dir)
    out_dir = Path(args.output_dir)

    in_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = list_texts(in_dir)
    if not files:
        print(f'未在 {in_dir} 找到 .txt 文稿')
        return

    for txt in files:
        process_text(txt, out_dir, args.seconds_per_seg, prefer_mp3=args.mp3)

    print(f'完成，输出目录：{out_dir}')


if __name__ == '__main__':
    main()
