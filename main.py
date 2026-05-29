import sys
import os

# Windows 无控制台 GUI 程序中 stdout/stderr 为 None，必须在所有 import 之前修复
# 否则 ctranslate2/faster-whisper/huggingface_hub 等库加载时会崩溃
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from app.main_window import MainWindow


def _get_icon_path() -> str:
    """获取应用图标路径，兼容开发环境和打包环境。"""
    if getattr(sys, 'frozen', False):
        # 打包环境
        base_dir = os.path.dirname(sys.executable)
        # PyInstaller 6.x: 数据在 _internal/ 下
        icon_path = os.path.join(base_dir, '_internal', 'resources', 'icons', 'app.ico')
        if os.path.exists(icon_path):
            return icon_path
        # 回退到根目录
        icon_path = os.path.join(base_dir, 'resources', 'icons', 'app.ico')
        if os.path.exists(icon_path):
            return icon_path
    else:
        # 开发环境
        base_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(base_dir, 'resources', 'icons', 'app.ico')
        if os.path.exists(icon_path):
            return icon_path
    return ""


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("V2T - 音视频转文字")
    app.setOrganizationName("V2T")

    # 设置运行时窗口图标（标题栏 + 任务栏）
    icon_path = _get_icon_path()
    if icon_path:
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
