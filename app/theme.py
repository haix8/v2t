"""主题管理 - 支持深色/浅色模式自动切换"""
import sys
import platform


def is_dark_mode() -> bool:
    """检测系统是否为深色模式"""
    if platform.system() == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            )
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)
            return value == 0
        except Exception:
            return False
    elif platform.system() == "Darwin":
        try:
            import subprocess
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True, text=True
            )
            return "Dark" in result.stdout
        except Exception:
            return False
    else:
        # Linux - 检查常见环境变量或默认浅色
        return False


LIGHT_THEME = """
    QMainWindow {
        background-color: #f5f5f5;
    }
    QGroupBox {
        font-weight: bold;
        border: 1px solid #d0d0d0;
        border-radius: 6px;
        margin-top: 8px;
        padding-top: 14px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
    }
    QPushButton {
        padding: 6px 14px;
        border: 1px solid #c0c0c0;
        border-radius: 4px;
        background-color: #ffffff;
        min-height: 24px;
    }
    QPushButton:hover {
        background-color: #e8e8e8;
    }
    QPushButton:pressed {
        background-color: #d0d0d0;
    }
    QPushButton:disabled {
        background-color: #f0f0f0;
        color: #a0a0a0;
        border-color: #e0e0e0;
    }
    QPushButton#btnStart {
        background-color: #4caf50;
        color: white;
        border-color: #43a047;
        font-weight: bold;
    }
    QPushButton#btnStart:hover {
        background-color: #43a047;
    }
    QPushButton#btnStart:pressed {
        background-color: #388e3c;
    }
    QPushButton#btnStart:disabled {
        background-color: #a5d6a7;
        color: #e8f5e9;
        border-color: #a5d6a7;
    }
    QPushButton#btnCancel {
        background-color: #f44336;
        color: white;
        border-color: #e53935;
        font-weight: bold;
    }
    QPushButton#btnCancel:hover {
        background-color: #e53935;
    }
    QPushButton#btnCancel:pressed {
        background-color: #c62828;
    }
    QPushButton#btnCancel:disabled {
        background-color: #ef9a9a;
        color: #ffebee;
        border-color: #ef9a9a;
    }
    QProgressBar {
        border: 1px solid #d0d0d0;
        border-radius: 4px;
        text-align: center;
        height: 20px;
    }
    QProgressBar::chunk {
        background-color: #4caf50;
        border-radius: 3px;
    }
    QComboBox {
        padding: 4px 8px;
        border: 1px solid #c0c0c0;
        border-radius: 4px;
        background-color: #ffffff;
        min-height: 24px;
    }
    QComboBox QAbstractItemView {
        outline: none;
        selection-background-color: #1a73e8;
        selection-color: #ffffff;
    }
    QComboBox QAbstractItemView::item {
        padding: 4px 8px;
        min-height: 24px;
    }
    QComboBox QAbstractItemView::item:selected {
        background-color: #1a73e8;
        color: #ffffff;
    }
    QListWidget {
        border: 1px solid #d0d0d0;
        border-radius: 4px;
        background-color: #ffffff;
    }
    QPlainTextEdit {
        border: 1px solid #d0d0d0;
        border-radius: 4px;
        background-color: #ffffff;
        font-family: monospace;
        font-size: 13px;
    }
    QLabel {
        color: #333333;
    }
"""

DARK_THEME = """
    QMainWindow {
        background-color: #1e1e1e;
    }
    QGroupBox {
        font-weight: bold;
        border: 1px solid #444444;
        border-radius: 6px;
        margin-top: 8px;
        padding-top: 14px;
        color: #e0e0e0;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        color: #e0e0e0;
    }
    QWidget {
        color: #e0e0e0;
    }
    QPushButton {
        padding: 6px 14px;
        border: 1px solid #555555;
        border-radius: 4px;
        background-color: #2d2d2d;
        color: #e0e0e0;
        min-height: 24px;
    }
    QPushButton:hover {
        background-color: #3d3d3d;
    }
    QPushButton:pressed {
        background-color: #4d4d4d;
    }
    QPushButton:disabled {
        background-color: #252525;
        color: #666666;
        border-color: #333333;
    }
    QPushButton#btnStart {
        background-color: #2e7d32;
        color: white;
        border-color: #1b5e20;
        font-weight: bold;
    }
    QPushButton#btnStart:hover {
        background-color: #388e3c;
    }
    QPushButton#btnStart:pressed {
        background-color: #1b5e20;
    }
    QPushButton#btnStart:disabled {
        background-color: #1a3d1c;
        color: #4a6b4c;
        border-color: #1a3d1c;
    }
    QPushButton#btnCancel {
        background-color: #c62828;
        color: white;
        border-color: #b71c1c;
        font-weight: bold;
    }
    QPushButton#btnCancel:hover {
        background-color: #d32f2f;
    }
    QPushButton#btnCancel:pressed {
        background-color: #b71c1c;
    }
    QPushButton#btnCancel:disabled {
        background-color: #3d1515;
        color: #6b4a4a;
        border-color: #3d1515;
    }
    QProgressBar {
        border: 1px solid #444444;
        border-radius: 4px;
        text-align: center;
        height: 20px;
        background-color: #2d2d2d;
        color: #e0e0e0;
    }
    QProgressBar::chunk {
        background-color: #4caf50;
        border-radius: 3px;
    }
    QComboBox {
        padding: 4px 8px;
        border: 1px solid #555555;
        border-radius: 4px;
        background-color: #2d2d2d;
        color: #e0e0e0;
        min-height: 24px;
    }
    QComboBox QAbstractItemView {
        outline: none;
        background-color: #2d2d2d;
        color: #e0e0e0;
        selection-background-color: #1a73e8;
        selection-color: #ffffff;
    }
    QComboBox QAbstractItemView::item {
        padding: 4px 8px;
        min-height: 24px;
    }
    QComboBox QAbstractItemView::item:selected {
        background-color: #1a73e8;
        color: #ffffff;
    }
    QComboBox::drop-down {
        border: none;
    }
    QListWidget {
        border: 1px solid #444444;
        border-radius: 4px;
        background-color: #2d2d2d;
        color: #e0e0e0;
    }
    QListWidget::item:selected {
        background-color: #1a73e8;
        color: #ffffff;
    }
    QPlainTextEdit {
        border: 1px solid #444444;
        border-radius: 4px;
        background-color: #2d2d2d;
        color: #e0e0e0;
        font-family: monospace;
        font-size: 13px;
    }
    QLabel {
        color: #e0e0e0;
    }
    QSplitter::handle {
        background-color: #333333;
    }
"""


def get_stylesheet() -> str:
    """根据系统主题返回对应的样式表"""
    if is_dark_mode():
        return DARK_THEME
    return LIGHT_THEME
