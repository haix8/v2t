import sys
import os
import io

# Windows 无控制台 GUI 程序中 stdout/stderr 为 None，必须在所有 import 之前修复
# 否则 ctranslate2/faster-whisper/huggingface_hub 等库加载时会崩溃
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')

from PySide6.QtWidgets import QApplication
from app.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("V2T - 音视频转文字")
    app.setOrganizationName("V2T")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
