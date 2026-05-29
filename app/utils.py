"""工具函数"""
from pathlib import Path
from typing import Optional


# 支持的音频格式
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"}

# 支持的视频格式
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".webm", ".flv", ".m4v"}

# 所有支持的格式
SUPPORTED_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS


def get_file_filter() -> str:
    """获取文件对话框的过滤器字符串"""
    audio_exts = " ".join(f"*{ext}" for ext in sorted(AUDIO_EXTENSIONS))
    video_exts = " ".join(f"*{ext}" for ext in sorted(VIDEO_EXTENSIONS))
    all_exts = " ".join(f"*{ext}" for ext in sorted(SUPPORTED_EXTENSIONS))
    return (
        f"所有支持的格式 ({all_exts});;"
        f"音频文件 ({audio_exts});;"
        f"视频文件 ({video_exts});;"
        f"所有文件 (*)"
    )


def is_supported_file(file_path: str) -> bool:
    """检查文件是否为支持的格式"""
    ext = Path(file_path).suffix.lower()
    return ext in SUPPORTED_EXTENSIONS


def get_output_path(input_path: str, output_dir: Optional[str], fmt: str = "txt") -> str:
    """
    根据输入文件路径生成输出文件路径
    
    Args:
        input_path: 输入文件路径
        output_dir: 输出目录, None 表示与输入文件同目录
        fmt: 输出格式 (txt/srt)
    """
    input_file = Path(input_path)
    stem = input_file.stem
    
    if output_dir:
        out_dir = Path(output_dir)
    else:
        out_dir = input_file.parent
    
    output_path = out_dir / f"{stem}.{fmt}"
    
    # 如果文件已存在, 添加序号
    counter = 1
    while output_path.exists():
        output_path = out_dir / f"{stem}_{counter}.{fmt}"
        counter += 1
    
    return str(output_path)


def format_time_srt(seconds: float) -> str:
    """将秒数格式化为 SRT 时间格式 (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def segments_to_srt(segments: list) -> str:
    """将段落列表转换为 SRT 字幕格式文本"""
    lines = []
    for i, seg in enumerate(segments, 1):
        start = format_time_srt(seg["start"])
        end = format_time_srt(seg["end"])
        lines.append(f"{i}")
        lines.append(f"{start} --> {end}")
        lines.append(seg["text"])
        lines.append("")
    return "\n".join(lines)


def segments_to_txt(segments: list) -> str:
    """将段落列表转换为纯文本"""
    return "\n".join(seg["text"] for seg in segments if seg["text"])


def format_duration(seconds: float) -> str:
    """格式化时长为可读字符串"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}小时{minutes}分{secs}秒"
    elif minutes > 0:
        return f"{minutes}分{secs}秒"
    else:
        return f"{secs}秒"
