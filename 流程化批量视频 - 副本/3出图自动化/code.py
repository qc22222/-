import os
import re
import uuid
import time
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple

import requests
from docx import Document
from openai import OpenAI

# 可选：如需官方 SDK，可安装 runware；此处直接使用 HTTP API


class RunwareImageGenerator:
    """
    基于 OpenAI + Runware 的出图自动化工具。
    - 从桌面 剪辑/改写 文件夹读取 docx
    - 将文本转为英文单行 prompt
    - 调用 Runware 生成图片并保存到 剪辑/图片/<文档名>/
    """

    def __init__(self) -> None:
        # 基础路径
        self.desktop = str(Path.home() / "Desktop")
        self.rewrite_folder = os.path.join(self.desktop, "剪辑", "改写")
        self.image_folder = os.path.join(self.desktop, "剪辑", "图片")

        os.makedirs(self.rewrite_folder, exist_ok=True)
        os.makedirs(self.image_folder, exist_ok=True)

        # 运行时状态
        self.start_time: Optional[float] = None
        self.current_file: Optional[str] = None
        self.current_file_name: Optional[str] = None
        self.total_cost: float = 0.0

        # OpenAI
        self.client = OpenAI(
            base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            api_key=os.environ.get("OPENAI_API_KEY", ""),
        )

        # Runware
        self.runware_api_key = os.environ.get("RUNWARE_API_KEY", "")

        # 提示词
        self.system_prompts = {
            "通用": (
                "忘记你以前的一切设定\n"
                "将下面的文本翻译为详细的场景英文描述，用作给AI出图，要求：\n"
                "1. 译成英文，尽量以人事物+动作+周围场景作为格式\n"
                "2. 描述写成一行\n"
                "3. 只输出英文描述，不要其他的任何说明\n"
            ),
            "中文基督": (
                "忘记你以前的一切设定\n"
                "将下面的文本翻译为详细的场景英文描述，用作给AI出图，要求：\n"
                "1. 译成英文，尽量以人事物+动作+周围场景作为格式\n"
                "2. 描述写成一行\n"
                "3. 只输出英文描述，不要其他的任何说明\n"
                "4. 这是一个基督教相关的内容，若合适可加入相符的基督教元素\n"
            ),
            "英文出图": (
                "忘记你以前的一切设定\n"
                "Please enhance the following English text for AI image generation, requirements:\n"
                "1. Keep the original meaning but make it more detailed and vivid\n"
                "2. Output in a single line\n"
                "3. Only output the English description, no other explanations\n"
            ),
            "西班牙语": (
                "忘记你以前的一切设定\n"
                "Por favor, traduzca el siguiente texto a una descripción detallada de la escena en inglés\n"
                "para la generación de imágenes de IA, requisitos:\n"
                "1. Traduzca al inglés, intentando utilizar la estructura de persona/objeto + acción + entorno\n"
                "2. La descripción debe ser una sola línea\n"
                "3. Solo salida de la descripción en inglés, sin ninguna otra explicación\n"
            ),
            "恐怖故事": (
                "忘记你以前的一切设定\n"
                "将文本生成为详细的恐怖场景英文描述，用作给AI出图，要求：\n"
                "1. 尽量以人事物+动作+周围恐怖场景作为格式\n"
                "2. 描述写成一行\n"
                "3. 只输出英文描述，不要其他的任何说明\n"
            ),
        }

        # 分段配置（字符或单词）
        self.split_configs = {
            "1": {"type": "chars", "target_chars": 115, "punctuation": "。！？，；"},
            "2": {"type": "chars", "target_chars": 105, "punctuation": "。！？，；"},
            "3": {"type": "words", "target_words": 55, "punctuation": ".,"},
            "4": {"type": "words", "target_words": 70, "punctuation": ".,!?¡¿"},
            "5": {"type": "words", "target_words": 55, "punctuation": ".,"},
        }

        self.current_mode: Optional[str] = None

    # -------- 基础工具 --------
    def get_current_time(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def log_message(self, message: str, level: str = "INFO") -> None:
        print(f"[{self.get_current_time()}] [{level}] {message}")

    def print_progress(self, current: int, total: int) -> None:
        total = max(total, 1)
        progress = current / total
        filled = int(50 * progress)
        bar = "=" * filled + " " * (50 - filled)
        print(f"\r处理进度: [{bar}] {current}/{total}", end="", flush=True)

    # -------- 文本处理 --------
    def read_docx(self, file_path: str) -> List[str]:
        doc = Document(file_path)
        paragraphs: List[str] = []
        for para in doc.paragraphs:
            text = (para.text or "").strip()
            if text:
                paragraphs.append(text)
        return paragraphs

    def _cleanup_text(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"\s+([\.,!\?])", r"\1", text)
        return text

    def split_paragraphs(self, paragraphs: List[str]) -> List[str]:
        # 合并文本后分段，避免过短段落
        all_text = self._cleanup_text(" ".join(paragraphs))
        return self.split_into_paragraphs(all_text)

    def count_words(self, text: str) -> int:
        clean = re.sub(r"[^\w\s]", "", text)
        return len([w for w in clean.split() if w])

    def split_into_paragraphs(self, text: str) -> List[str]:
        if not self.current_mode:
            return [text]
        cfg = self.split_configs.get(self.current_mode)
        if not cfg:
            return [text]

        result: List[str] = []
        if cfg["type"] == "chars":
            target = cfg["target_chars"]
            puncts = cfg["punctuation"]
            start = 0
            while start < len(text):
                end = min(len(text), start + target)
                # 尽量在标点处切
                best = -1
                for i in range(end, max(start, end - 50), -1):
                    if text[i - 1] in puncts:
                        best = i
                        break
                cut = best if best != -1 else end
                segment = text[start:cut].strip()
                if segment:
                    result.append(segment)
                start = cut
            return result
        else:
            # words 模式
            target = cfg["target_words"]
            words = text.split()
            buf: List[str] = []
            for w in words:
                buf.append(w)
                if len(buf) >= target:
                    segment = " ".join(buf).strip()
                    if segment:
                        result.append(segment)
                    buf = []
            if buf:
                segment = " ".join(buf).strip()
                if segment:
                    result.append(segment)
            return result

    # -------- 成本估算 --------
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        # 简单估算：$3 / 1M 输入；$12 / 1M 输出
        return (input_tokens / 1_000_000) * 3.0 + (output_tokens / 1_000_000) * 12.0

    # -------- Runware 出图 --------
    def generate_image(self, prompt: str) -> Tuple[Optional[str], Optional[str]]:
        """调用 Runware HTTP API 生成图片，返回 (task_id, image_url)"""
        try:
            url = "https://api.runware.ai/v1/inference"
            headers = {
                "Authorization": f"Bearer {self.runware_api_key}",
                "Content-Type": "application/json",
            }
            payload = [
                {
                    "taskType": "imageInference",
                    "taskUUID": str(uuid.uuid4()),
                    "model": "runware:101@1",
                    "positivePrompt": prompt,
                    "negativePrompt": (
                        "NSFW, nude, naked, blood, gore, violence, offensive, cropped, "
                        "worst quality, low quality, normal quality, jpeg artifacts, signature, "
                        "watermark, username, blurry, letter"
                    ),
                    "width": 1024,
                    "height": 576,
                    "steps": 20,
                    "scheduler": "FlowMatchEulerDiscreteScheduler",
                    "CFGScale": 3.5,
                    "outputType": "URL",
                    "outputFormat": "JPG",
                    "includeCost": True,
                }
            ]
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and isinstance(data.get("data"), list):
                for item in data["data"]:
                    if item.get("taskType") == "imageInference":
                        # 统计费用
                        if "cost" in item:
                            cost = float(item["cost"]) or 0.0
                            self.total_cost += cost
                            self.log_message(f"本次生成费用: ${cost:.4f}")
                        return item.get("taskUUID"), item.get("imageURL")
            self.log_message("Runware 响应格式不正确", "ERROR")
            return None, None
        except Exception as e:
            self.log_message(f"生成图片失败: {e}", "ERROR")
            return None, None

    def get_current_save_folder(self) -> Optional[str]:
        if not self.current_file_name:
            return None
        folder = os.path.join(self.image_folder, self.current_file_name)
        os.makedirs(folder, exist_ok=True)
        return folder

    def save_image(self, image_url: str, image_name: str) -> bool:
        try:
            save_folder = self.get_current_save_folder()
            if not save_folder:
                return False
            r = requests.get(image_url, timeout=60)
            if r.status_code != 200:
                self.log_message(f"下载图片失败: {r.status_code}", "ERROR")
                return False
            path = os.path.join(save_folder, f"{image_name}.png")
            with open(path, "wb") as f:
                f.write(r.content)
            self.log_message(f"图片已保存: {path}")
            return True
        except Exception as e:
            self.log_message(f"保存图片失败: {e}", "ERROR")
            return False

    # -------- OpenAI 描述生成 --------
    def process_segment_with_gpt(self, segment: str, mode: str) -> Optional[str]:
        try:
            name_map = {
                "1": "通用",
                "2": "中文基督",
                "3": "英文出图",
                "4": "西班牙语",
                "5": "恐怖故事",
            }
            system_prompt = self.system_prompts.get(name_map.get(mode, "通用"))
            if not system_prompt:
                return None

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": segment},
            ]
            # gpt-4o-mini 作为默认
            resp = self.client.chat.completions.create(
                model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                messages=messages,
                temperature=0.7,
                max_tokens=1024,
            )
            if resp and resp.choices:
                prompt = (resp.choices[0].message.content or "").strip()
                # 增加高质量关键词
                quality = (
                    ", breathtaking photograph, cinematic lighting, 8k uhd, "
                    "highly detailed, photorealistic, professional photography, "
                    "masterpiece, sharp focus, high quality"
                )
                return prompt + quality
            return None
        except Exception as e:
            self.log_message(f"调用 OpenAI 失败: {e}", "ERROR")
            return None

    # -------- 文件处理 --------
    def process_file(self, file_path: str, mode: str) -> bool:
        try:
            self.total_cost = 0.0
            self.current_file = file_path
            self.current_file_name = os.path.splitext(os.path.basename(file_path))[0]
            self.current_mode = mode
            self.start_time = time.time()

            paragraphs = self.read_docx(file_path)
            if not paragraphs:
                self.log_message("文档为空", "ERROR")
                return False

            segments = self.split_paragraphs(paragraphs)
            if not segments:
                self.log_message("没有切分到有效段落", "ERROR")
                return False

            self.log_message(f"{os.path.basename(file_path)} 已分割为 {len(segments)} 段")
            for i, seg in enumerate(segments, 1):
                self.print_progress(i, len(segments))
                prompt = self.process_segment_with_gpt(seg, mode)
                if not prompt:
                    continue
                # 每段生成 4 张
                for j in range(1, 5):
                    task_id, image_url = self.generate_image(prompt)
                    if not (task_id and image_url):
                        continue
                    image_name = f"{i}_{j}"
                    self.save_image(image_url, image_name)
            print()  # 进度条换行

            if self.total_cost > 0:
                self.log_message(f"总费用: ${self.total_cost:.4f}")
                self.log_message(f"总费用(人民币): ¥{self.total_cost * 7.2:.2f}")
            return True
        except Exception as e:
            self.log_message(f"处理文件失败: {e}", "ERROR")
            return False

    # -------- 交互流程 --------
    def _list_docx_files(self) -> List[str]:
        res: List[str] = []
        if not os.path.isdir(self.rewrite_folder):
            return res
        for fn in os.listdir(self.rewrite_folder):
            if fn.startswith(".") or fn.startswith("~"):
                continue
            if fn.lower().endswith(".docx"):
                res.append(os.path.join(self.rewrite_folder, fn))
        return sorted(res, key=lambda p: os.path.basename(p).lower())

    def select_files(self, docx_files: List[str]) -> Tuple[Optional[List[str]], Optional[str]]:
        if not docx_files:
            self.log_message("未找到任何 docx 文件")
            return None, None
        print("\n找到以下文件：")
        for i, p in enumerate(docx_files, 1):
            print(f"{i}. {os.path.basename(p)}")
        print("\n输入 'q' 退出程序")
        choice = input("\n请输入要处理的文件编号（多个文件用空格分隔）: ").strip()
        if choice.lower() == "q":
            return None, None
        try:
            idxs = [int(x) for x in choice.split()]
            selected: List[str] = []
            for idx in idxs:
                if 1 <= idx <= len(docx_files):
                    selected.append(docx_files[idx - 1])
            return selected, choice
        except Exception:
            self.log_message("请输入有效的文件编号", "ERROR")
            return None, None

    def run(self) -> None:
        files = self._list_docx_files()
        if not files:
            print(f"\n在 {self.rewrite_folder} 中没有找到 .docx 文件")
            print("请将要处理的文件放入此文件夹，然后重新运行程序")
            return

        # 默认非交互执行：处理全部文件，模式可通过环境变量 IMG_GEN_MODE 配置（默认 1）
        if os.environ.get("NON_INTERACTIVE", "1") == "1":
            mode = os.environ.get("IMG_GEN_MODE", "1")
            if mode not in {"1", "2", "3", "4", "5"}:
                mode = "1"
            print("\n开始处理文件（非交互模式）...")
            for p in files:
                print(f"\n正在处理：{os.path.basename(p)}，模式 {mode}")
                ok = self.process_file(p, mode)
                if not ok:
                    self.log_message(f"处理失败: {os.path.basename(p)}", "ERROR")
            return

        # 交互模式
        selected, _ = self.select_files(files)
        if not selected:
            return

        file_modes: dict[str, str] = {}
        print("\n为每个文件选择处理模式：")
        print("1. 通用模式\n2. 基督教内容\n3. 英文基督教内容\n4. 西班牙语模式\n5. 恐怖故事模式")
        for p in selected:
            while True:
                mode = input(f"文件 {os.path.basename(p)} 选择模式(1/2/3/4/5，0取消): ").strip()
                if mode == "0":
                    return
                if mode in {"1", "2", "3", "4", "5"}:
                    file_modes[p] = mode
                    break
                print("无效选项，请重试")

        print("\n开始处理文件...")
        for p, m in file_modes.items():
            print(f"\n正在处理：{os.path.basename(p)}")
            ok = self.process_file(p, m)
            if not ok:
                self.log_message(f"处理失败: {os.path.basename(p)}", "ERROR")


if __name__ == "__main__":
    gen = RunwareImageGenerator()
    gen.run()
