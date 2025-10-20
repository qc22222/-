#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
3. 出图自动化（占位实现）

- 自动读取：../2_text_rewriter/output/rewritten_texts/*.docx
- 输出图片：./output/generated_images/

说明：
为优先跑通流程，本脚本不强制调用任何在线出图 API，而是根据文稿段落生成占位图片。
每个段落生成一张 1024x576 的 PNG 图片，图片上写入文稿前 40 个字符。
后续可替换为 Gemini/Runware 等实际出图逻辑。

.env 支持：
  - GEMINI_API_KEY 等密钥后续可在此使用（当前不强制）。

示例：
  python 3_image_generator/code.py \
    --input-dir "流程化批量视频/2_text_rewriter/output/rewritten_texts" \
    --output-dir "流程化批量视频/3_image_generator/output/generated_images"
"""

import argparse
from pathlib import Path
from typing import List

from docx import Document
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

DEFAULT_INPUT_DIR = (Path(__file__).resolve().parents[1]
                     / '2_text_rewriter' / 'output' / 'rewritten_texts')
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / 'output' / 'generated_images'


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


def draw_placeholder(text: str, save_path: Path, size=(1024, 576)) -> None:
    img = Image.new('RGB', size, color=(245, 245, 245))
    draw = ImageDraw.Draw(img)
    # Try to use a default font; fallback if not available
    try:
        font = ImageFont.truetype('DejaVuSans.ttf', 28)
    except Exception:
        font = ImageFont.load_default()
    display = (text[:40] + '...') if len(text) > 40 else text
    # Word wrap manually to fit width
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


def process_doc(docx_path: Path, out_dir: Path) -> List[Path]:
    out_paths: List[Path] = []
    paras = extract_paragraphs(docx_path)
    if not paras:
        return out_paths
    base = docx_path.stem
    for idx, para in enumerate(paras, start=1):
        save_path = out_dir / f"{base}_{idx:03d}.png"
        draw_placeholder(para, save_path)
        out_paths.append(save_path)
    return out_paths


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description='出图自动化（占位实现）')
    parser.add_argument('--input-dir', type=str, default=str(DEFAULT_INPUT_DIR), help='改写后文稿目录')
    parser.add_argument('--output-dir', type=str, default=str(DEFAULT_OUTPUT_DIR), help='图片输出目录')

    args = parser.parse_args()

    in_dir = Path(args.input_dir)
    out_dir = Path(args.output_dir)

    in_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = list_docx_files(in_dir)
    if not files:
        print(f'未在 {in_dir} 找到 .docx 文稿')
        return

    total = 0
    for docx in files:
        outs = process_doc(docx, out_dir)
        print(f'{docx.name}: 生成 {len(outs)} 张图片')
        total += len(outs)
    print(f'完成，共生成 {total} 张图片，输出目录：{out_dir}')


if __name__ == '__main__':
    main()
