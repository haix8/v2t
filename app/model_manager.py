"""模型管理业务逻辑模块

提供 Whisper 模型的状态检测、完整性验证、下载管理和删除等功能。
"""
import os
import sys
import shutil
from enum import Enum
from typing import Optional


# 模型元信息
MODEL_INFO: dict[str, dict] = {
    "tiny": {"size_mb": 75, "params": "39M", "speed": "~32x", "description": "最快速度，适合实时场景", "languages": 99},
    "base": {"size_mb": 142, "params": "74M", "speed": "~16x", "description": "速度与质量平衡", "languages": 99},
    "small": {"size_mb": 466, "params": "244M", "speed": "~6x", "description": "较好质量，适合一般转录", "languages": 99},
    "medium": {"size_mb": 1500, "params": "769M", "speed": "~2x", "description": "高质量转录，适合对精度要求较高的场景", "languages": 99},
    "large-v3": {"size_mb": 3100, "params": "1550M", "speed": "~1x", "description": "最高精度，适合专业场景", "languages": 99},
}

# 模型必要文件列表
_REQUIRED_FILES = ["config.json", "model.bin", "tokenizer.json", "vocabulary.txt"]


class ModelStatus(Enum):
    """模型状态枚举"""

    DOWNLOADED = "downloaded"
    NOT_DOWNLOADED = "not_downloaded"
    DOWNLOADING = "downloading"


class ModelManager:
    """Whisper 模型管理器，负责模型的状态管理和文件操作。"""

    def __init__(self) -> None:
        # 存储正在下载的模型名称
        self._downloading: set[str] = set()

    def get_models_dir(self) -> str:
        """获取模型存储目录，支持打包环境和开发环境。

        Returns:
            模型存储目录的绝对路径。
        """
        if getattr(sys, "frozen", False):
            # 打包环境：exe 同级目录下的 models/
            base_dir = os.path.dirname(sys.executable)
            # 也检查 _internal 下（PyInstaller 6.x）
            internal_path = os.path.join(base_dir, "_internal", "models")
            if os.path.isdir(internal_path):
                return internal_path
            return os.path.join(base_dir, "models")
        else:
            # 开发环境：项目根目录下的 models/
            project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            return os.path.join(project_dir, "models")

    def get_model_status(self, model_name: str) -> ModelStatus:
        """检测本地模型状态。

        Args:
            model_name: 模型名称（如 "tiny", "medium", "large-v3"）。

        Returns:
            模型当前状态。
        """
        if model_name in self._downloading:
            return ModelStatus.DOWNLOADING

        models_dir = self.get_models_dir()
        model_path = os.path.join(models_dir, f"faster-whisper-{model_name}")

        if os.path.isdir(model_path) and os.path.isfile(os.path.join(model_path, "model.bin")):
            return ModelStatus.DOWNLOADED

        return ModelStatus.NOT_DOWNLOADED

    def validate_model(self, model_name: str) -> tuple[bool, str]:
        """验证模型完整性。

        检查模型目录中是否包含所有必要文件。

        Args:
            model_name: 模型名称。

        Returns:
            (是否有效, 消息) 的元组。
        """
        models_dir = self.get_models_dir()
        model_path = os.path.join(models_dir, f"faster-whisper-{model_name}")

        if not os.path.isdir(model_path):
            return False, f"模型目录不存在: {model_path}"

        missing_files: list[str] = []
        for filename in _REQUIRED_FILES:
            if not os.path.isfile(os.path.join(model_path, filename)):
                missing_files.append(filename)

        if missing_files:
            return False, f"缺少文件: {', '.join(missing_files)}"

        return True, "模型完整"

    def delete_model(self, model_name: str) -> tuple[bool, str]:
        """删除本地模型文件。

        Args:
            model_name: 模型名称。

        Returns:
            (是否成功, 消息) 的元组。
        """
        models_dir = self.get_models_dir()
        model_path = os.path.join(models_dir, f"faster-whisper-{model_name}")

        if not os.path.isdir(model_path):
            return False, f"模型目录不存在: {model_path}"

        try:
            shutil.rmtree(model_path)
            return True, f"已删除模型: {model_name}"
        except OSError as e:
            return False, f"删除失败: {e}"

    def get_repo_id(self, model_name: str) -> str:
        """返回模型对应的 Hugging Face repo_id。

        Args:
            model_name: 模型名称。

        Returns:
            Hugging Face 仓库 ID。
        """
        return f"Systran/faster-whisper-{model_name}"

    def get_all_models_status(self) -> dict[str, ModelStatus]:
        """返回所有模型的状态字典。

        Returns:
            键为模型名称，值为 ModelStatus 的字典。
        """
        return {name: self.get_model_status(name) for name in MODEL_INFO}

    def get_model_info(self, model_name: str) -> dict:
        """获取模型的详细信息。

        Args:
            model_name: 模型名称。

        Returns:
            模型元信息字典，若模型名称无效则返回空字典。
        """
        return MODEL_INFO.get(model_name, {})

    def set_downloading(self, model_name: str) -> None:
        """标记模型为下载中。

        Args:
            model_name: 模型名称。
        """
        self._downloading.add(model_name)

    def set_download_finished(self, model_name: str) -> None:
        """标记模型下载完成。

        Args:
            model_name: 模型名称。
        """
        self._downloading.discard(model_name)

    def format_size(self, size_mb: int) -> str:
        """格式化模型大小显示。

        Args:
            size_mb: 模型大小（MB）。

        Returns:
            格式化后的字符串（如 1500 -> '1.5 GB'）。
        """
        if size_mb >= 1000:
            return f"{size_mb / 1000:.1f} GB"
        return f"{size_mb} MB"
