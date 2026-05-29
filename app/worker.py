"""转录工作线程"""
from PySide6.QtCore import QThread, Signal
from app.transcriber import Transcriber


class TranscribeWorker(QThread):
    """后台转录工作线程"""

    progress_updated = Signal(int, float)  # file_index, progress (0.0-1.0)
    file_completed = Signal(int, dict)     # file_index, result
    all_completed = Signal()
    error_occurred = Signal(int, str)      # file_index, error_message
    status_message = Signal(str)           # 状态文本

    def __init__(self, files: list[str], model_size: str, language: str, parent=None):
        super().__init__(parent)
        self.files = files
        self.model_size = model_size
        self.language = language
        self._cancelled = False

    def cancel(self):
        """请求取消转录"""
        self._cancelled = True

    def run(self):
        """执行转录任务"""
        # 加载模型
        try:
            self.status_message.emit(f"正在加载模型 ({self.model_size})...")
            transcriber = Transcriber(model_size=self.model_size)
            transcriber.load_model()
        except Exception as e:
            self.error_occurred.emit(-1, f"模型加载失败: {str(e)}")
            return

        # 逐文件转录
        for i, file_path in enumerate(self.files):
            if self._cancelled:
                self.status_message.emit("已取消")
                return

            self.status_message.emit(f"正在转录 ({i + 1}/{len(self.files)}): {file_path}")

            try:
                def on_progress(p: float, idx: int = i) -> None:
                    if not self._cancelled:
                        self.progress_updated.emit(idx, p)

                result = transcriber.transcribe(
                    audio_path=file_path,
                    language=self.language if self.language != "auto" else None,
                    progress_callback=on_progress,
                    cancel_check=lambda: self._cancelled,
                )

                if not self._cancelled:
                    self.file_completed.emit(i, result)
            except Exception as e:
                if not self._cancelled:
                    self.error_occurred.emit(i, str(e))

            if self._cancelled:
                self.status_message.emit("已取消")
                return

        if not self._cancelled:
            self.all_completed.emit()
