"""模型下载工作线程"""
import os
import sys
from PySide6.QtCore import QThread, Signal


class ModelDownloadWorker(QThread):
    """后台下载 Whisper 模型的工作线程"""

    # 信号定义
    download_progress = Signal(str, float)   # (model_name, progress 0.0-1.0)
    download_completed = Signal(str)          # (model_name)
    download_failed = Signal(str, str)        # (model_name, error_message)
    status_message = Signal(str)              # 状态文本

    def __init__(self, model_name: str, models_dir: str, parent=None):
        """初始化下载工作线程。

        Args:
            model_name: 模型名称（如 'medium', 'large-v3'）
            models_dir: 模型存储目录的绝对路径
            parent: 父对象
        """
        super().__init__(parent)
        self._model_name = model_name
        self._models_dir = models_dir
        self._cancelled = False

    def cancel(self):
        """请求取消下载"""
        self._cancelled = True

    @property
    def model_name(self) -> str:
        """返回当前下载的模型名称"""
        return self._model_name

    def run(self):
        """执行模型下载"""
        # 1. 处理 sys.stdout/stderr 为 None 的情况（GUI 打包环境）
        if sys.stdout is None:
            sys.stdout = open(os.devnull, 'w', encoding='utf-8')
        if sys.stderr is None:
            sys.stderr = open(os.devnull, 'w', encoding='utf-8')

        # 2. 准备目标目录
        model_dir_name = f"faster-whisper-{self._model_name}"
        local_dir = os.path.join(self._models_dir, model_dir_name)
        os.makedirs(local_dir, exist_ok=True)

        # 3. 构建 repo_id
        repo_id = f"Systran/faster-whisper-{self._model_name}"

        # 4. 发送状态
        self.status_message.emit(f"正在下载模型 {self._model_name}...")

        try:
            # 5. 调用 huggingface_hub 下载
            from huggingface_hub import snapshot_download

            # 发送初始进度信号
            self.download_progress.emit(self._model_name, 0.0)

            if self._cancelled:
                return

            snapshot_download(
                repo_id=repo_id,
                local_dir=local_dir,
            )

            if self._cancelled:
                self.status_message.emit("下载已取消")
                return

            # 6. 下载完成
            self.download_progress.emit(self._model_name, 1.0)
            self.download_completed.emit(self._model_name)

        except Exception as e:
            if not self._cancelled:
                self.download_failed.emit(self._model_name, str(e))
