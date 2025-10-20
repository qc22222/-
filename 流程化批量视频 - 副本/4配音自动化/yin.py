import json
from typing import List, Dict, Any


class TTSGenerator:
    """
    配音与字幕辅助工具（简化版占位实现）。
    提供：
    - JSON 字幕数据转 SRT
    - SRT 时间格式互转
    - 简单字幕切割与优化
    """

    def __init__(self) -> None:
        # 预留配置位（Azure / MiniMax / Whisper 等），此处不做实际初始化
        self.azure_subscription_key: str = ""
        self.azure_region: str = ""
        self.azure_voice_name: str = ""

    # ---------- 时间与格式 ----------
    def ms_to_srt_time(self, milliseconds: float) -> str:
        milliseconds = float(milliseconds)
        seconds, ms = divmod(milliseconds, 1000)
        minutes, seconds = divmod(int(seconds), 60)
        hours, minutes = divmod(int(minutes), 60)
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d},{int(ms):03d}"

    def srt_time_to_ms(self, time_str: str) -> int:
        try:
            main, ms = time_str.split(",")
            h, m, s = main.split(":")
            return int(h) * 3600000 + int(m) * 60000 + int(s) * 1000 + int(ms)
        except Exception:
            return 0

    # ---------- 字幕处理 ----------
    def split_subtitle_text(self, text: str) -> List[str]:
        """
        将字幕文本切割为多段，每段不超过 13 个字符。
        若第 13 个字符为中文，向后寻找最近的标点后切割。
        """
        if not text or len(text) <= 13:
            return [text]

        punctuations = [
            "，", "。", "、", "；", "：", "？", "！", "…", "\"", "'",
            "）", "】", "》", "」", "』", "〕", "｝", "］",
            ",", ".", ";", ":", "?", "!", ")", "]", "}",
        ]

        res: List[str] = []
        start = 0
        while start < len(text):
            if len(text) - start <= 13:
                res.append(text[start:])
                break
            cut = start + 13
            is_chinese = "\u4e00" <= text[cut] <= "\u9fff"
            if is_chinese:
                found = False
                for i in range(cut, min(cut + 10, len(text))):
                    if text[i] in punctuations:
                        cut = i + 1
                        found = True
                        break
                if not found and (len(text) - cut) < 5:
                    cut = len(text)
            res.append(text[start:cut])
            start = cut
        return res

    def convert_json_to_srt(self, subtitle_data: List[Dict[str, Any]]) -> str:
        """将 MiniMax 或类似结构的字幕 JSON 转为 SRT 字符串。"""
        if not isinstance(subtitle_data, list):
            return ""

        lines: List[str] = []
        idx = 1
        for item in subtitle_data:
            # 尝试多字段兼容
            start = item.get("start_time") or item.get("begin_time") or item.get("start") or item.get("begin") or item.get("startTime") or item.get("beginTime") or item.get("time_begin")
            end = item.get("end_time") or item.get("finish_time") or item.get("end") or item.get("finish") or item.get("endTime") or item.get("finishTime") or item.get("time_end")
            text = item.get("text") or item.get("content") or item.get("subtitle") or item.get("words") or item.get("sentence")
            if start is None or end is None or text is None:
                continue
            try:
                start_ms = float(start)
                end_ms = float(end)
            except Exception:
                continue
            start_str = self.ms_to_srt_time(start_ms)
            end_str = self.ms_to_srt_time(end_ms)
            lines.append(f"{idx}\n{start_str} --> {end_str}\n{text}\n")
            idx += 1
        return "\n".join(lines)

    def optimize_srt_file(self, srt_path: str) -> bool:
        """将过长字幕切为更短的多段，同时平均分配时间。"""
        try:
            with open(srt_path, "r", encoding="utf-8") as f:
                content = f.read()
            blocks = [b for b in content.strip().split("\n\n") if b.strip()]
            new_blocks: List[str] = []
            new_idx = 1
            for b in blocks:
                parts = b.splitlines()
                if len(parts) < 3:
                    continue
                # 原有时间轴与文本
                try:
                    time_line = parts[1]
                    text = "\n".join(parts[2:])
                    start_str, end_str = [x.strip() for x in time_line.split("-->")]
                    start_ms = self.srt_time_to_ms(start_str)
                    end_ms = self.srt_time_to_ms(end_str)
                    if end_ms <= start_ms:
                        continue
                except Exception:
                    continue
                segments = self.split_subtitle_text(text)
                if len(segments) <= 1:
                    new_blocks.append(f"{new_idx}\n{time_line}\n{text}")
                    new_idx += 1
                    continue
                total = end_ms - start_ms
                step = total / len(segments)
                for i, seg in enumerate(segments):
                    seg_start = int(start_ms + i * step)
                    seg_end = int(start_ms + (i + 1) * step)
                    new_blocks.append(
                        f"{new_idx}\n{self.ms_to_srt_time(seg_start)} --> {self.ms_to_srt_time(seg_end)}\n{seg}"
                    )
                    new_idx += 1
            with open(srt_path, "w", encoding="utf-8") as f:
                f.write("\n\n".join(new_blocks))
            return True
        except Exception:
            return False
