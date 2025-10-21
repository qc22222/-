#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
3. 文本分段出图（占位实现）

- 输入：automated_video_workflow/3_segment_image_generator/input/texts/ 下的 .txt（或通过 --input-dir 指定）
- 输出：automated_video_workflow/3_segment_image_generator/output/generated_images/ 下的占位图

说明：
读取改写后的文本（每一非空行视作一个段落），为每个段落生成一张占位图片（1024x576），
图片上写入该行前若干字符。后续可替换为 Gemini/Runware 等真实出图。

示例：
  python automated_video_workflow/3_segment_image_generator/batch_generate.py \
    --input-dir automated_video_workflow/2_subtitle_rewriter/output/rewritten_texts \
    --output-dir automated_video_workflow/3_segment_image_generator/output/generated_images
"""

import argparse
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

DEFAULT_INPUT_DIR = Path(__file__).resolve().parent / 'input' / 'texts'
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / 'output' / 'generated_images'


def list_texts(input_dir: Path) -> List[Path]:
    return sorted([p for p in input_dir.glob('*.txt') if p.is_file()])


def read_nonempty_lines(path: Path) -> List[str]:
    lines = path.read_text(encoding='utf-8', errors='ignore').splitlines()
    return [ln.strip() for ln in lines if ln.strip()]


def draw_placeholder(text: str, save_path: Path, size=(1024, 576)) -> None:
    img = Image.new('RGB', size, color=(245, 245, 245))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype('DejaVuSans.ttf', 28)
    except Exception:
        font = ImageFont.load_default()
    display = (text[:40] + '...') if len(text) > 40 else text
    # 简易换行
    lines = []
    words = display.split(' ')
    line = ''
    for w in words:
        test = (line + ' ' + w).strip()
        if draw.textlength(test, font=font) <= size[0] - 80:
            line = test
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    y = size[1] // 2 - (len(lines) * 32) // 2
    for ln in lines:
        w = draw.textlength(ln, font=font)
        x = (size[0] - w) // 2
        draw.text((x, y), ln, fill=(20, 20, 20), font=font)
        y += 36
    save_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(save_path)


def process_text(txt_path: Path, out_dir: Path) -> List[Path]:
    out_paths: List[Path] = []
    paras = read_nonempty_lines(txt_path)
    if not paras:
        return out_paths
    base = txt_path.stem
    for idx, para in enumerate(paras, start=1):
        save_path = out_dir / f"{base}_{idx:03d}.png"
        draw_placeholder(para, save_path)
        out_paths.append(save_path)
    return out_paths


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description='文本分段出图（占位实现）')
    parser.add_argument('--input-dir', type=str, default=str(DEFAULT_INPUT_DIR), help='改写文本目录（TXT）')
    parser.add_argument('--output-dir', type=str, default=str(DEFAULT_OUTPUT_DIR), help='图片输出目录')

    args = parser.parse_args()

    in_dir = Path(args.input_dir)
    out_dir = Path(args.output_dir)
    in_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = list_texts(in_dir)
    if not files:
        print(f'未在 {in_dir} 找到 .txt 文本')
        return

    total = 0
    for txt in files:
        outs = process_text(txt, out_dir)
        print(f'{txt.name}: 生成 {len(outs)} 张图片')
        total += len(outs)
    print(f'完成，共生成 {total} 张图片，输出目录：{out_dir}')


if __name__ == '__main__':
    main()
