"""Whisper 转录引擎封装"""
import os
from typing import Optional, Callable
from faster_whisper import WhisperModel


# 可用模型列表
AVAILABLE_MODELS = ["tiny", "base", "small", "medium", "large-v3"]

# 支持的语言
SUPPORTED_LANGUAGES = {
    "auto": "自动检测",
    "zh": "中文",
    "en": "English",
    "ja": "日本語",
    "ko": "한국어",
    "fr": "Français",
    "de": "Deutsch",
    "es": "Español",
    "ru": "Русский",
}


class Transcriber:
    """faster-whisper 转录器"""

    def __init__(self, model_size: str = "base", device: str = "auto", compute_type: str = "auto"):
        """
        初始化转录器
        
        Args:
            model_size: 模型大小 (tiny/base/small/medium/large-v3)
            device: 设备 ("auto", "cpu", "cuda")
            compute_type: 计算类型 ("auto" 会根据设备自动选择)
        """
        self.model_size = model_size
        self.model: Optional[WhisperModel] = None
        
        # 自动选择设备和计算类型
        if device == "auto":
            try:
                import torch
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                self.device = "cpu"
        else:
            self.device = device
            
        if compute_type == "auto":
            self.compute_type = "float16" if self.device == "cuda" else "int8"
        else:
            self.compute_type = compute_type

    def load_model(self):
        """加载模型"""
        # 确保内置 ffmpeg 在 PATH 中
        from app.utils import get_ffmpeg_path
        ffmpeg_path = get_ffmpeg_path()
        if ffmpeg_path:
            ffmpeg_dir = os.path.dirname(ffmpeg_path)
            if ffmpeg_dir not in os.environ.get('PATH', ''):
                os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ.get('PATH', '')

        # 查找本地预置模型
        model_path = self._find_local_model()
        if model_path:
            # 本地已有模型，直接加载
            model_source = model_path
        else:
            # 本地没有，下载到项目 models/ 目录
            model_source = self._download_model()

        self.model = WhisperModel(
            model_source,
            device=self.device,
            compute_type=self.compute_type,
        )

    def _get_models_dir(self) -> str:
        """获取模型存储目录"""
        import sys
        if getattr(sys, 'frozen', False):
            # 打包环境：exe 同级目录下的 models/
            base_dir = os.path.dirname(sys.executable)
            # 也检查 _internal 下（PyInstaller 6.x）
            internal_path = os.path.join(base_dir, '_internal', 'models')
            if os.path.isdir(internal_path):
                return internal_path
            return os.path.join(base_dir, 'models')
        else:
            # 开发环境：项目根目录下的 models/
            project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            return os.path.join(project_dir, 'models')

    def _find_local_model(self) -> Optional[str]:
        """查找本地预置模型目录，如果存在且包含 model.bin 则返回路径"""
        models_dir = self._get_models_dir()
        model_dir_name = f"faster-whisper-{self.model_size}"
        model_path = os.path.join(models_dir, model_dir_name)

        if os.path.isdir(model_path) and os.path.isfile(os.path.join(model_path, 'model.bin')):
            return model_path
        return None

    def _download_model(self) -> str:
        """下载模型到项目 models/ 目录，返回本地路径"""
        import sys
        
        # 在无控制台的 GUI 程序中，sys.stdout/stderr 可能为 None
        if sys.stdout is None:
            sys.stdout = open(os.devnull, 'w', encoding='utf-8')
        if sys.stderr is None:
            sys.stderr = open(os.devnull, 'w', encoding='utf-8')
        
        from huggingface_hub import snapshot_download

        models_dir = self._get_models_dir()
        model_dir_name = f"faster-whisper-{self.model_size}"
        local_dir = os.path.join(models_dir, model_dir_name)
        os.makedirs(local_dir, exist_ok=True)

        repo_id = f"Systran/faster-whisper-{self.model_size}"
        snapshot_download(
            repo_id=repo_id,
            local_dir=local_dir,
            local_dir_use_symlinks=False,
        )
        return local_dir

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> dict:
        """
        转录音频文件
        
        Args:
            audio_path: 音频文件路径
            language: 语言代码, None 表示自动检测
            progress_callback: 进度回调函数, 参数为 0.0~1.0 的浮点数
            
        Returns:
            dict: {
                "text": 完整文本,
                "segments": [{"start": float, "end": float, "text": str}, ...],
                "language": 检测到的语言,
                "duration": 音频总时长
            }
        """
        if self.model is None:
            self.load_model()

        # 设置语言参数
        lang = language if language and language != "auto" else None

        segments_iter, info = self.model.transcribe(
            audio_path,
            language=lang,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )

        duration = info.duration
        detected_language = info.language
        
        segments = []
        full_text_parts = []

        for segment in segments_iter:
            segments.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip(),
            })
            full_text_parts.append(segment.text.strip())

            # 进度回调
            if progress_callback and duration > 0:
                progress = min(segment.end / duration, 1.0)
                progress_callback(progress)

        return {
            "text": "\n".join(full_text_parts),
            "segments": segments,
            "language": detected_language,
            "duration": duration,
        }
