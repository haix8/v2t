"""工具函数"""
import os
import shutil
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


def get_ffmpeg_path() -> str:
    """获取 ffmpeg 可执行文件路径，优先使用内置版本"""
    import sys

    ffmpeg_name = 'ffmpeg.exe' if os.name == 'nt' else 'ffmpeg'

    # 打包后的路径
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包环境
        base_dir = os.path.dirname(sys.executable)
        # PyInstaller 6.x 将文件放在 _internal/ 下
        search_paths = [
            os.path.join(base_dir, '_internal', 'ffmpeg', ffmpeg_name),
            os.path.join(base_dir, 'ffmpeg', ffmpeg_name),
            os.path.join(base_dir, '_internal', ffmpeg_name),
            os.path.join(base_dir, ffmpeg_name),
        ]
        for p in search_paths:
            if os.path.isfile(p):
                return p
    else:
        # 开发环境，检查项目目录
        project_dir = Path(__file__).parent.parent
        bundled = project_dir / 'ffmpeg' / ffmpeg_name
        if bundled.is_file():
            return str(bundled)

    # 回退到系统 PATH
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    return ""


def check_ffmpeg() -> bool:
    """检查 ffmpeg 是否可用"""
    return bool(get_ffmpeg_path())


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


def download_ffmpeg() -> bool:
    """
    自动下载 ffmpeg 到项目/程序的 ffmpeg/ 目录
    仅支持 Windows，返回是否下载成功
    """
    import sys
    import platform
    import urllib.request
    import zipfile
    import tempfile

    if platform.system() != "Windows":
        return False

    # 确定目标目录
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = str(Path(__file__).parent.parent)

    ffmpeg_dir = os.path.join(base_dir, 'ffmpeg')
    os.makedirs(ffmpeg_dir, exist_ok=True)

    target_path = os.path.join(ffmpeg_dir, 'ffmpeg.exe')
    if os.path.isfile(target_path):
        return True

    # 从 GitHub 下载 ffmpeg essentials
    # 使用 BtbN 的 release（稳定可靠）
    url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"

    try:
        # 下载到临时文件
        temp_zip = os.path.join(tempfile.gettempdir(), 'ffmpeg_download.zip')
        urllib.request.urlretrieve(url, temp_zip)

        # 解压并提取 ffmpeg.exe
        with zipfile.ZipFile(temp_zip, 'r') as zf:
            # 在 zip 中查找 ffmpeg.exe
            for name in zf.namelist():
                if name.endswith('bin/ffmpeg.exe'):
                    # 提取到目标位置
                    with zf.open(name) as src, open(target_path, 'wb') as dst:
                        shutil.copyfileobj(src, dst)
                    break

        # 清理临时文件
        if os.path.exists(temp_zip):
            os.remove(temp_zip)

        return os.path.isfile(target_path)
    except Exception:
        return False
