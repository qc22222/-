import os
import json
import uuid
from glob import glob
from typing import List, Dict, Any, Optional


MIN_IMAGE_DURATION = 5  # 最小图片展示时间（秒）


def get_latest_draft_folder() -> str:
    """获取最新的剪映草稿文件夹。"""
    pattern = os.path.expanduser("~/Desktop/Youtube/剪映draft/JianyingPro Drafts/*/draft_content.json")
    files = glob(pattern)
    if not files:
        raise FileNotFoundError("未找到剪映草稿文件")
    latest = max(files, key=os.path.getmtime)
    return os.path.dirname(latest)


def microsec_to_time(microseconds: int) -> str:
    total_seconds = microseconds / 1_000_000
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)
    ms = int((total_seconds % 1) * 1000)
    return f"{minutes:02d}:{seconds:02d}:{ms:03d}"


def format_duration(microseconds: int) -> str:
    return f"{microseconds / 1_000_000:.2f}秒"


def find_images_in_folder(folder_path: Optional[str] = None) -> List[str]:
    if folder_path is None:
        folder_path = os.path.expanduser("~/Desktop/Youtube/images")
    exts = ["jpg", "jpeg", "png", "gif", "webp"]
    files: List[str] = []
    for ext in exts:
        files.extend(glob(os.path.join(folder_path, f"*.{ext}")))
    if not files:
        # 兼容当前目录
        for ext in exts:
            files.extend(glob(os.path.join(os.getcwd(), f"*.{ext}")))
    if not files:
        raise FileNotFoundError("未找到图片文件，请确保图片文件夹中包含图片")
    return files


def import_images_to_draft(draft: Dict[str, Any], image_files: List[str]) -> Dict[str, Any]:
    materials = draft.setdefault("materials", {})
    videos = materials.setdefault("videos", [])
    for path in image_files:
        file_name = os.path.basename(path)
        mat = {
            "id": str(uuid.uuid4()),
            "type": "photo",
            "material_name": file_name,
            "path": path,
            "width": 1920,
            "height": 1080,
            "has_audio": False,
            "duration": 10_000_000,  # 默认 10s
        }
        videos.append(mat)
    return draft


def create_common_keyframes(start_time: int, duration: int, movement_type: str = "left") -> List[Dict[str, Any]]:
    # 简化的关键帧模板，仅返回占位结构
    kf_x = {
        "id": str(uuid.uuid4()),
        "property_type": "KFTypePositionX",
        "keyframe_list": [
            {"time_offset": 0, "values": [-0.21 if movement_type == "left" else 0.21]},
            {"time_offset": duration, "values": [0.21 if movement_type == "left" else -0.21]},
        ],
    }
    kf_y = {
        "id": str(uuid.uuid4()),
        "property_type": "KFTypePositionY",
        "keyframe_list": [
            {"time_offset": 0, "values": [0]},
            {"time_offset": duration, "values": [0]},
        ],
    }
    return [kf_x, kf_y]


_last_animation: Optional[str] = None


def get_random_animation() -> Dict[str, Any]:
    # 简化：返回一个固定的“渐显”动画占位结构
    return {
        "id": str(uuid.uuid4()),
        "type": "sticker_animation",
        "animations": [
            {
                "id": "fade_in",
                "name": "渐显",
                "category_id": "in",
                "category_name": "入场",
                "duration": 700_000,
                "type": "in",
                "start": 0,
            }
        ],
    }


def find_next_subtitle_time(subtitle_segments: List[Dict[str, Any]], current_start_time: int) -> int:
    min_possible_end = current_start_time + MIN_IMAGE_DURATION * 1_000_000
    for sub in subtitle_segments:
        start = sub.get("target_timerange", {}).get("start", 0)
        if start > min_possible_end:
            return start
    return min_possible_end


def add_effects_to_segment(segment: Dict[str, Any]) -> Dict[str, Any]:
    segment["extra_material_refs"] = [
        "E312DFCC-91BF-47D1-831A-999CE06AF820",
        "BAE4FFEE-2A02-4D91-9C10-1CFA0B5A9FA7",
    ]
    return segment


def add_effect_track(draft: Dict[str, Any], segments: List[Dict[str, Any]]) -> Dict[str, Any]:
    track = {
        "id": str(uuid.uuid4()),
        "type": "effect",
        "name": "",
        "attribute": 0,
        "flag": 0,
        "segments": [],
        "is_default_name": True,
    }
    materials = draft.setdefault("materials", {})
    video_effects = materials.setdefault("video_effects", [])

    for i, seg in enumerate(segments):
        anim = get_random_animation()
        video_effects.append(anim)
        eff_seg = {
            "id": str(uuid.uuid4()),
            "material_id": anim["id"],
            "target_timerange": seg.get("target_timerange", {"start": 0, "duration": 1_000_000}),
            "track_render_index": 1,
            "render_index": 11_000 + i,
            "visible": True,
            "volume": 1.0,
        }
        track["segments"].append(eff_seg)

    tracks = draft.setdefault("tracks", [])
    tracks.append(track)
    return draft


def sync_images_with_subtitles_in_draft(draft: Dict[str, Any]) -> Dict[str, Any]:
    # 简化：在有 text 轨道的基础上，为每个字幕生成一个图片片段并对齐持续时间
    text_track = None
    for t in draft.get("tracks", []):
        if t.get("type") == "text":
            text_track = t
            break
    if not text_track:
        return draft

    subtitle_segments = text_track.get("segments", [])
    # 创建图片轨道
    image_track = {
        "id": str(uuid.uuid4()),
        "type": "video",
        "name": "images",
        "segments": [],
    }

    materials = draft.get("materials", {})
    images = materials.get("videos", [])

    current_image_idx = 0
    for sub in subtitle_segments:
        if not images:
            break
        img = images[current_image_idx % len(images)]
        current_image_idx += 1

        start = sub.get("target_timerange", {}).get("start", 0)
        end = find_next_subtitle_time(subtitle_segments, start)
        duration = max(1_000_000 * MIN_IMAGE_DURATION, end - start)

        seg = {
            "id": str(uuid.uuid4()),
            "material_id": img.get("id"),
            "source_timerange": None,
            "target_timerange": {"start": start, "duration": duration},
            "keyframe_refs": [],
            "common_keyframes": create_common_keyframes(start, duration),
            "visible": True,
        }
        image_track["segments"].append(add_effects_to_segment(seg))

    draft.setdefault("tracks", []).append(image_track)
    return draft


__all__ = [
    "get_latest_draft_folder",
    "microsec_to_time",
    "format_duration",
    "find_images_in_folder",
    "import_images_to_draft",
    "create_common_keyframes",
    "get_random_animation",
    "find_next_subtitle_time",
    "add_effects_to_segment",
    "add_effect_track",
    "sync_images_with_subtitles_in_draft",
]
