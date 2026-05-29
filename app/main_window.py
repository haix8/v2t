"""主窗口 UI"""
import os
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QListWidget, QListWidgetItem, QComboBox, QPushButton, QLabel,
    QProgressBar, QPlainTextEdit, QFileDialog, QGroupBox, QMessageBox,
    QApplication, QListView,
)

from app.transcriber import AVAILABLE_MODELS, SUPPORTED_LANGUAGES
from app.worker import TranscribeWorker
from app.settings import AppSettings
from app.utils import (
    get_file_filter, is_supported_file, get_output_path,
    segments_to_srt, segments_to_txt, format_duration,
)
from app.model_manager import ModelManager, ModelStatus, MODEL_INFO
from app.model_manager_dialog import ModelManagerDialog


class MainWindow(QMainWindow):
    """V2T 主窗口"""

    def __init__(self):
        super().__init__()
        self._settings = AppSettings()
        self._worker: TranscribeWorker | None = None
        self._results: dict[int, dict] = {}  # file_index -> result
        self._completed_count = 0

        self.setWindowTitle("V2T - 音视频转文字")
        self.setMinimumSize(900, 650)
        self.setAcceptDrops(True)

        self._setup_ui()
        self._setup_styles()
        self._load_settings()

    # ─── UI 构建 ─────────────────────────────────────────────

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # 左栏
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 4, 0)
        self._setup_left_panel(left_layout)
        splitter.addWidget(left_widget)

        # 右栏
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(4, 0, 0, 0)
        self._setup_right_panel(right_layout)
        splitter.addWidget(right_widget)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([300, 600])

    def _setup_left_panel(self, layout: QVBoxLayout):
        # ── 文件列表 ──
        file_group = QGroupBox("文件列表")
        file_layout = QVBoxLayout(file_group)

        self._file_list = QListWidget()
        self._file_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        file_layout.addWidget(self._file_list)

        btn_row = QHBoxLayout()
        self._btn_add = QPushButton("添加文件")
        self._btn_add.clicked.connect(self._add_files)
        btn_row.addWidget(self._btn_add)

        self._btn_remove = QPushButton("移除选中")
        self._btn_remove.clicked.connect(self._remove_selected)
        btn_row.addWidget(self._btn_remove)

        self._btn_clear = QPushButton("清空列表")
        self._btn_clear.clicked.connect(self._clear_list)
        btn_row.addWidget(self._btn_clear)

        file_layout.addLayout(btn_row)
        layout.addWidget(file_group)

        # ── 设置 ──
        settings_group = QGroupBox("设置")
        settings_layout = QVBoxLayout(settings_group)

        # 模型选择
        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("模型:"))
        self._combo_model = QComboBox()
        self._combo_model.setView(QListView())
        self._init_model_combo()
        self._combo_model.currentIndexChanged.connect(self._on_settings_changed)
        model_row.addWidget(self._combo_model, 1)

        self._btn_manage_models = QPushButton("管理")
        self._btn_manage_models.setObjectName("btnManageModels")
        self._btn_manage_models.clicked.connect(self._open_model_manager)
        model_row.addWidget(self._btn_manage_models)
        settings_layout.addLayout(model_row)

        # 语言选择
        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel("语言:"))
        self._combo_lang = QComboBox()
        self._combo_lang.setView(QListView())
        for code, name in SUPPORTED_LANGUAGES.items():
            self._combo_lang.addItem(name, code)
        self._combo_lang.currentIndexChanged.connect(self._on_settings_changed)
        lang_row.addWidget(self._combo_lang, 1)
        settings_layout.addLayout(lang_row)

        # 输出格式
        fmt_row = QHBoxLayout()
        fmt_row.addWidget(QLabel("格式:"))
        self._combo_format = QComboBox()
        self._combo_format.setView(QListView())
        self._combo_format.addItem("TXT", "txt")
        self._combo_format.addItem("SRT", "srt")
        self._combo_format.currentIndexChanged.connect(self._on_settings_changed)
        fmt_row.addWidget(self._combo_format, 1)
        settings_layout.addLayout(fmt_row)

        layout.addWidget(settings_group)

        # ── 控制按钮 ──
        ctrl_row = QHBoxLayout()
        self._btn_start = QPushButton("开始转录")
        self._btn_start.setObjectName("btnStart")
        self._btn_start.clicked.connect(self._start_transcription)
        ctrl_row.addWidget(self._btn_start)

        self._btn_cancel = QPushButton("取消")
        self._btn_cancel.setObjectName("btnCancel")
        self._btn_cancel.setEnabled(False)
        self._btn_cancel.clicked.connect(self._cancel_transcription)
        ctrl_row.addWidget(self._btn_cancel)

        layout.addLayout(ctrl_row)
        layout.addStretch()

    def _setup_right_panel(self, layout: QVBoxLayout):
        # ── 进度区域 ──
        progress_group = QGroupBox("进度")
        progress_layout = QVBoxLayout(progress_group)

        self._label_status = QLabel("就绪")
        self._label_status.setWordWrap(True)
        progress_layout.addWidget(self._label_status)

        progress_layout.addWidget(QLabel("当前文件:"))
        self._progress_file = QProgressBar()
        self._progress_file.setRange(0, 100)
        self._progress_file.setValue(0)
        self._progress_file.setFormat("%p%")
        progress_layout.addWidget(self._progress_file)

        progress_layout.addWidget(QLabel("总体进度:"))
        self._progress_total = QProgressBar()
        self._progress_total.setRange(0, 100)
        self._progress_total.setValue(0)
        self._progress_total.setFormat("%p%")
        progress_layout.addWidget(self._progress_total)

        layout.addWidget(progress_group)

        # ── 结果区域 ──
        result_group = QGroupBox("转录结果")
        result_layout = QVBoxLayout(result_group)

        self._text_result = QPlainTextEdit()
        self._text_result.setReadOnly(False)
        self._text_result.setPlaceholderText("转录结果将显示在此处...")
        result_layout.addWidget(self._text_result)

        result_btn_row = QHBoxLayout()
        self._btn_save = QPushButton("保存结果")
        self._btn_save.clicked.connect(self._save_result)
        result_btn_row.addWidget(self._btn_save)

        self._btn_copy = QPushButton("复制到剪贴板")
        self._btn_copy.clicked.connect(self._copy_to_clipboard)
        result_btn_row.addWidget(self._btn_copy)

        result_layout.addLayout(result_btn_row)
        layout.addWidget(result_group, 1)

    def _setup_styles(self):
        from app.theme import get_stylesheet
        self.setStyleSheet(get_stylesheet())

    # ─── 拖拽支持 ─────────────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        added = 0
        for url in urls:
            if url.isLocalFile():
                path = url.toLocalFile()
                if is_supported_file(path):
                    self._add_file_to_list(path)
                    added += 1
        if added == 0:
            self._label_status.setText("未找到支持的音视频文件")

    # ─── 文件管理 ─────────────────────────────────────────────

    def _add_file_to_list(self, file_path: str) -> None:
        """添加单个文件到列表（去重）"""
        existing = {
            self._file_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self._file_list.count())
        }
        if file_path not in existing:
            item = QListWidgetItem(Path(file_path).name)
            item.setData(Qt.ItemDataRole.UserRole, file_path)
            item.setToolTip(file_path)
            self._file_list.addItem(item)

    def _add_files(self):
        start_dir = self._settings.last_open_directory or ""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择音视频文件", start_dir, get_file_filter()
        )
        if files:
            self._settings.last_open_directory = str(Path(files[0]).parent)
            for f in files:
                self._add_file_to_list(f)

    def _remove_selected(self):
        items = self._file_list.selectedItems()
        for item in items:
            row = self._file_list.row(item)
            self._file_list.takeItem(row)

    def _clear_list(self):
        self._file_list.clear()
        self._results.clear()
        self._completed_count = 0
        self._text_result.clear()

    # ─── 转录控制 ─────────────────────────────────────────────

    def _start_transcription(self):
        # 收集文件列表
        files = [
            self._file_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self._file_list.count())
        ]
        if not files:
            QMessageBox.information(self, "提示", "请先添加要转录的文件")
            return

        # 重置状态
        self._results.clear()
        self._completed_count = 0
        self._progress_file.setValue(0)
        self._progress_total.setValue(0)
        self._text_result.clear()

        # 创建并启动 worker
        model_size = self._combo_model.currentData()
        language = self._combo_lang.currentData()

        self._worker = TranscribeWorker(
            files=files,
            model_size=model_size,
            language=language,
            parent=self,
        )
        self._worker.progress_updated.connect(self._on_progress_updated)
        self._worker.file_completed.connect(self._on_file_completed)
        self._worker.all_completed.connect(self._on_all_completed)
        self._worker.error_occurred.connect(self._on_error_occurred)
        self._worker.status_message.connect(self._on_status_message)
        self._worker.finished.connect(self._reset_ui_state)

        # 切换按钮状态
        self._btn_start.setEnabled(False)
        self._btn_cancel.setEnabled(True)
        self._set_settings_enabled(False)

        self._worker.start()

    def _cancel_transcription(self):
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._label_status.setText("正在取消...")
            self._btn_cancel.setEnabled(False)

            # 启动超时检查定时器
            self._cancel_timer = QTimer(self)
            self._cancel_timer.setSingleShot(True)
            self._cancel_timer.timeout.connect(self._force_cancel)
            self._cancel_timer.start(5000)  # 5秒超时

    def _force_cancel(self):
        """超时后强制终止转录线程"""
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait(2000)
            self._label_status.setText("已强制取消")
            self._reset_ui_state()

    def _set_settings_enabled(self, enabled: bool):
        """批量启用/禁用设置控件"""
        self._combo_model.setEnabled(enabled)
        self._combo_lang.setEnabled(enabled)
        self._btn_add.setEnabled(enabled)
        self._btn_remove.setEnabled(enabled)
        self._btn_clear.setEnabled(enabled)

    # ─── Worker 信号槽 ────────────────────────────────────────

    def _on_progress_updated(self, file_index: int, progress: float):
        self._progress_file.setValue(int(progress * 100))

        # 计算总体进度: 已完成文件数 + 当前文件进度
        total = self._file_list.count()
        if total > 0:
            overall = (self._completed_count + progress) / total
            self._progress_total.setValue(int(overall * 100))

    def _on_file_completed(self, file_index: int, result: dict):
        self._results[file_index] = result
        self._completed_count += 1

        total = self._file_list.count()
        self._progress_total.setValue(int(self._completed_count / total * 100))
        self._progress_file.setValue(100)

        # 在结果编辑器中追加内容
        file_path = self._file_list.item(file_index).data(Qt.ItemDataRole.UserRole)
        filename = Path(file_path).name
        duration_str = format_duration(result.get("duration", 0))
        lang = result.get("language", "")

        self._text_result.appendPlainText(f"═══ {filename} ═══")
        self._text_result.appendPlainText(f"时长: {duration_str}  语言: {lang}")
        self._text_result.appendPlainText("")
        self._text_result.appendPlainText(result.get("text", ""))
        self._text_result.appendPlainText("")
        self._text_result.appendPlainText("")

    def _on_all_completed(self):
        self._label_status.setText("全部转录完成")
        self._reset_ui_state()
        total = self._file_list.count()
        self._progress_total.setValue(100)
        self._progress_file.setValue(100)

    def _on_error_occurred(self, file_index: int, message: str):
        if file_index < 0:
            # 模型加载失败
            self._label_status.setText(f"错误: {message}")
            self._reset_ui_state()
            QMessageBox.critical(self, "错误", message)
        else:
            file_path = self._file_list.item(file_index).data(Qt.ItemDataRole.UserRole)
            filename = Path(file_path).name
            self._label_status.setText(f"转录失败: {filename}")
            self._text_result.appendPlainText(f"!!! {filename} 转录失败: {message}")
            self._text_result.appendPlainText("")

            # 即使单个文件失败，也计入完成数以正确计算总进度
            self._completed_count += 1
            total = self._file_list.count()
            if total > 0:
                self._progress_total.setValue(int(self._completed_count / total * 100))

    def _on_status_message(self, message: str):
        self._label_status.setText(message)

    def _reset_ui_state(self):
        """重置按钮和设置控件状态"""
        # 清理取消超时定时器
        if hasattr(self, '_cancel_timer') and self._cancel_timer.isActive():
            self._cancel_timer.stop()
        self._btn_start.setEnabled(True)
        self._btn_cancel.setEnabled(False)
        self._set_settings_enabled(True)
        self._worker = None

    # ─── 结果操作 ─────────────────────────────────────────────

    def _save_result(self):
        text = self._text_result.toPlainText()
        if not text.strip():
            QMessageBox.information(self, "提示", "没有可保存的结果")
            return

        fmt = self._combo_format.currentData()  # "txt" or "srt"

        # 如果有结果数据，优先使用格式化函数
        if self._results:
            parts = []
            for idx in sorted(self._results.keys()):
                result = self._results[idx]
                file_path = self._file_list.item(idx).data(Qt.ItemDataRole.UserRole)
                segments = result.get("segments", [])

                if fmt == "srt":
                    parts.append(segments_to_srt(segments))
                else:
                    filename = Path(file_path).name
                    parts.append(f"═══ {filename} ═══")
                    parts.append(segments_to_txt(segments))

            content = "\n\n".join(parts)
        else:
            content = text

        # 确定默认保存路径
        output_dir = self._settings.output_directory or ""
        ext = fmt
        filter_str = "SRT 字幕文件 (*.srt)" if fmt == "srt" else "文本文件 (*.txt)"

        default_path = os.path.join(output_dir, f"转录结果.{ext}") if output_dir else f"转录结果.{ext}"

        save_path, _ = QFileDialog.getSaveFileName(
            self, "保存转录结果", default_path, f"{filter_str};;所有文件 (*)"
        )

        if save_path:
            try:
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self._label_status.setText(f"已保存到: {save_path}")
            except Exception as e:
                QMessageBox.critical(self, "保存失败", str(e))

    def _copy_to_clipboard(self):
        text = self._text_result.toPlainText()
        if not text.strip():
            return
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        self._label_status.setText("已复制到剪贴板")

    # ─── 模型管理 ─────────────────────────────────────────────

    def _init_model_combo(self):
        """初始化模型下拉框，标记未下载模型"""
        manager = ModelManager()
        self._combo_model.clear()
        for m in AVAILABLE_MODELS:
            status = manager.get_model_status(m)
            if status == ModelStatus.DOWNLOADED:
                display_text = m
            else:
                display_text = f"{m} (未下载)"
            self._combo_model.addItem(display_text, m)

    def _open_model_manager(self):
        """打开模型管理对话框"""
        dialog = ModelManagerDialog(self)
        dialog.model_changed.connect(self._refresh_model_combo)
        dialog.show()

    def _refresh_model_combo(self):
        """模型变更后刷新下拉框"""
        current_data = self._combo_model.currentData()
        self._combo_model.blockSignals(True)
        try:
            self._init_model_combo()
            # 恢复之前的选择
            idx = self._combo_model.findData(current_data)
            if idx >= 0:
                self._combo_model.setCurrentIndex(idx)
        finally:
            self._combo_model.blockSignals(False)

    # ─── 设置持久化 ───────────────────────────────────────────

    def _on_settings_changed(self):
        """设置变更时自动保存"""
        self._save_settings()

    def _save_settings(self):
        self._settings.model_size = self._combo_model.currentData() or "base"
        self._settings.language = self._combo_lang.currentData() or "auto"
        self._settings.output_format = self._combo_format.currentData() or "txt"

    def _load_settings(self):
        # 模型
        model = self._settings.model_size
        idx = self._combo_model.findData(model)
        if idx >= 0:
            self._combo_model.setCurrentIndex(idx)

        # 语言
        lang = self._settings.language
        idx = self._combo_lang.findData(lang)
        if idx >= 0:
            self._combo_lang.setCurrentIndex(idx)

        # 输出格式
        fmt = self._settings.output_format
        idx = self._combo_format.findData(fmt)
        if idx >= 0:
            self._combo_format.setCurrentIndex(idx)
