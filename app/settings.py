"""应用设置管理"""
from PySide6.QtCore import QSettings


class AppSettings:
    """持久化应用设置"""

    def __init__(self):
        self._settings = QSettings("V2T", "V2T-音视频转文字")

    @property
    def model_size(self) -> str:
        return self._settings.value("model_size", "base")

    @model_size.setter
    def model_size(self, value: str):
        self._settings.setValue("model_size", value)

    @property
    def language(self) -> str:
        return self._settings.value("language", "auto")

    @language.setter
    def language(self, value: str):
        self._settings.setValue("language", value)

    @property
    def output_format(self) -> str:
        return self._settings.value("output_format", "txt")

    @output_format.setter
    def output_format(self, value: str):
        self._settings.setValue("output_format", value)

    @property
    def output_directory(self) -> str:
        return self._settings.value("output_directory", "")

    @output_directory.setter
    def output_directory(self, value: str):
        self._settings.setValue("output_directory", value)

    @property
    def last_open_directory(self) -> str:
        return self._settings.value("last_open_directory", "")

    @last_open_directory.setter
    def last_open_directory(self, value: str):
        self._settings.setValue("last_open_directory", value)
