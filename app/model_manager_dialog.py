"""模型管理对话框

提供 Whisper 模型的可视化管理界面，包括模型列表、详情、下载、删除、
验证以及设为默认模型等功能。对话框为非模态，允许用户在管理模型的
同时继续与主窗口交互。
"""
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.model_download_worker import ModelDownloadWorker
from app.model_manager import MODEL_INFO, ModelManager, ModelStatus
from app.settings import AppSettings
from app.theme import get_stylesheet


class ModelManagerDialog(QDialog):
    """模型管理对话框

    提供完整的模型生命周期管理 UI：
    - 列表展示所有可用模型及其状态
    - 详情区展示选中模型的元信息
    - 下载/取消下载/删除/验证 操作
    - 设置默认模型并通知主窗口刷新
    """

    # 模型变更信号：在下载完成、删除或设为默认后发出，主窗口可据此刷新
    model_changed = Signal()

    # 状态对应的尾缀图标
    _STATUS_SUFFIX: dict[ModelStatus, str] = {
        ModelStatus.DOWNLOADED: " ●",
        ModelStatus.NOT_DOWNLOADED: " ○",
        ModelStatus.DOWNLOADING: " ⟳",
    }

    _STATUS_TEXT: dict[ModelStatus, str] = {
        ModelStatus.DOWNLOADED: "已下载",
        ModelStatus.NOT_DOWNLOADED: "未下载",
        ModelStatus.DOWNLOADING: "下载中",
    }

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """初始化对话框。

        Args:
            parent: 父窗口。
        """
        super().__init__(parent)

        self._manager: ModelManager = ModelManager()
        self._settings: AppSettings = AppSettings()
        self._download_worker: Optional[ModelDownloadWorker] = None

        # 对话框基础属性
        self.setWindowTitle("模型管理")
        self.setMinimumSize(550, 500)
        self.setModal(False)
        # 非模态：保留独立窗口标志，不阻塞主窗口
        self.setWindowFlag(Qt.WindowType.Window, True)

        # 应用样式
        self.setStyleSheet(get_stylesheet())

        self._build_ui()
        self._connect_signals()
        self._refresh_model_list()
        self._select_default_model()

    # ------------------------------------------------------------------
    # UI 构建
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        """构建对话框 UI 布局。"""
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        # ----- 模型列表 -----
        self._list_models = QListWidget(self)
        self._list_models.setObjectName("listModels")
        self._list_models.setMinimumHeight(150)
        root.addWidget(self._list_models)

        # ----- 模型详情区 -----
        details_box = QGroupBox("模型详情", self)
        details_layout = QVBoxLayout(details_box)
        details_layout.setSpacing(4)

        self._label_params = QLabel("参数量: -")
        self._label_size = QLabel("磁盘大小: -")
        self._label_desc = QLabel("推荐场景: -")
        self._label_speed = QLabel("转录速度: -")
        self._label_languages = QLabel("支持语言: -")

        for lbl in (
            self._label_params,
            self._label_size,
            self._label_desc,
            self._label_speed,
            self._label_languages,
        ):
            lbl.setWordWrap(True)
            details_layout.addWidget(lbl)

        root.addWidget(details_box)

        # ----- 操作按钮区 -----
        op_row = QHBoxLayout()
        op_row.setSpacing(8)

        self._btn_download = QPushButton("下载模型", self)
        self._btn_download.setObjectName("btnDownload")

        self._btn_cancel_download = QPushButton("取消下载", self)
        self._btn_cancel_download.setObjectName("btnCancel")
        self._btn_cancel_download.hide()

        self._btn_delete = QPushButton("删除模型", self)
        self._btn_delete.setObjectName("btnDelete")

        self._btn_validate = QPushButton("验证模型", self)
        self._btn_validate.setObjectName("btnValidate")

        op_row.addWidget(self._btn_download)
        op_row.addWidget(self._btn_cancel_download)
        op_row.addWidget(self._btn_delete)
        op_row.addWidget(self._btn_validate)
        op_row.addStretch()

        root.addLayout(op_row)

        # ----- 下载进度区 -----
        self._group_progress = QGroupBox("下载进度", self)
        progress_layout = QVBoxLayout(self._group_progress)
        progress_layout.setSpacing(4)

        self._progress_download = QProgressBar(self._group_progress)
        self._progress_download.setRange(0, 100)
        self._progress_download.setValue(0)
        self._progress_download.setTextVisible(True)

        self._label_download_status = QLabel("等待开始...", self._group_progress)
        self._label_download_status.setWordWrap(True)

        progress_layout.addWidget(self._progress_download)
        progress_layout.addWidget(self._label_download_status)
        self._group_progress.hide()
        root.addWidget(self._group_progress)

        root.addStretch()

        # ----- 底部按钮 -----
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()

        self._btn_set_default = QPushButton("设为默认", self)
        self._btn_set_default.setObjectName("btnSetDefault")

        self._btn_close = QPushButton("关闭", self)
        self._btn_close.setObjectName("btnClose")

        bottom_row.addWidget(self._btn_set_default)
        bottom_row.addWidget(self._btn_close)
        root.addLayout(bottom_row)

    def _connect_signals(self) -> None:
        """连接信号与槽。"""
        self._list_models.currentItemChanged.connect(self._on_model_selected)

        self._btn_download.clicked.connect(self._start_download)
        self._btn_cancel_download.clicked.connect(self._cancel_download)
        self._btn_delete.clicked.connect(self._delete_model)
        self._btn_validate.clicked.connect(self._validate_model)
        self._btn_set_default.clicked.connect(self._set_as_default)
        self._btn_close.clicked.connect(self.close)

    # ------------------------------------------------------------------
    # 列表与详情
    # ------------------------------------------------------------------
    def _refresh_model_list(self) -> None:
        """刷新模型列表，保留当前选中项。"""
        previous = self._current_model_name()
        self._list_models.blockSignals(True)
        self._list_models.clear()

        for model_name, info in MODEL_INFO.items():
            status = self._manager.get_model_status(model_name)
            text = self._format_list_row(model_name, info, status)

            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, model_name)
            self._list_models.addItem(item)

            if model_name == previous:
                self._list_models.setCurrentItem(item)

        self._list_models.blockSignals(False)

        # 若没有先前选中项，则默认选中第一项
        if self._list_models.currentRow() < 0 and self._list_models.count() > 0:
            self._list_models.setCurrentRow(0)
        else:
            # 手动触发一次刷新（信号被屏蔽时未触发）
            self._on_model_selected(self._list_models.currentItem(), None)

    def _format_list_row(
        self, model_name: str, info: dict, status: ModelStatus
    ) -> str:
        """格式化列表行文本。"""
        size_text = self._manager.format_size(info.get("size_mb", 0))
        params = info.get("params", "-")
        status_text = self._STATUS_TEXT.get(status, "未知")
        suffix = self._STATUS_SUFFIX.get(status, "")
        default_marker = " ★" if model_name == self._settings.model_size else ""
        # 使用全角空格美化对齐
        return (
            f"{model_name:<10}  |  {params}参数  |  {size_text:<8}  |  "
            f"{status_text}{suffix}{default_marker}"
        )

    def _select_default_model(self) -> None:
        """启动时定位到当前默认模型。"""
        target = self._settings.model_size
        for i in range(self._list_models.count()):
            item = self._list_models.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == target:
                self._list_models.setCurrentRow(i)
                return

    def _current_model_name(self) -> Optional[str]:
        """返回当前选中的模型名称。"""
        item = self._list_models.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    # ------------------------------------------------------------------
    # 槽：列表选择
    # ------------------------------------------------------------------
    def _on_model_selected(
        self,
        current: Optional[QListWidgetItem],
        _previous: Optional[QListWidgetItem],
    ) -> None:
        """列表选择变更：刷新详情并更新按钮可用状态。"""
        if current is None:
            self._clear_details()
            self._update_button_states(None)
            return

        model_name = current.data(Qt.ItemDataRole.UserRole)
        self._update_details(model_name)
        self._update_button_states(model_name)

    def _clear_details(self) -> None:
        """清空详情区。"""
        self._label_params.setText("参数量: -")
        self._label_size.setText("磁盘大小: -")
        self._label_desc.setText("推荐场景: -")
        self._label_speed.setText("转录速度: -")
        self._label_languages.setText("支持语言: -")

    def _update_details(self, model_name: str) -> None:
        """更新模型详情。"""
        info = self._manager.get_model_info(model_name)
        if not info:
            self._clear_details()
            return

        size_text = self._manager.format_size(info.get("size_mb", 0))
        self._label_params.setText(f"参数量: {info.get('params', '-')}")
        self._label_size.setText(f"磁盘大小: ~{size_text}")
        self._label_desc.setText(f"推荐场景: {info.get('description', '-')}")
        self._label_speed.setText(
            f"转录速度: {info.get('speed', '-')} (相对实时)"
        )
        self._label_languages.setText(
            f"支持语言: {info.get('languages', '-')}种语言"
        )

    def _update_button_states(self, model_name: Optional[str]) -> None:
        """根据模型状态更新按钮可用性。"""
        if model_name is None:
            self._btn_download.setEnabled(False)
            self._btn_delete.setEnabled(False)
            self._btn_validate.setEnabled(False)
            self._btn_set_default.setEnabled(False)
            return

        status = self._manager.get_model_status(model_name)
        is_downloading_this = (
            self._download_worker is not None
            and self._download_worker.isRunning()
            and self._download_worker.model_name == model_name
        )
        any_downloading = (
            self._download_worker is not None and self._download_worker.isRunning()
        )

        # 下载/取消按钮：互斥显示
        if is_downloading_this:
            self._btn_download.hide()
            self._btn_cancel_download.show()
            self._btn_cancel_download.setEnabled(True)
        else:
            self._btn_cancel_download.hide()
            self._btn_download.show()
            self._btn_download.setEnabled(
                status == ModelStatus.NOT_DOWNLOADED and not any_downloading
            )

        self._btn_delete.setEnabled(
            status == ModelStatus.DOWNLOADED and not is_downloading_this
        )
        self._btn_validate.setEnabled(status == ModelStatus.DOWNLOADED)
        self._btn_set_default.setEnabled(status == ModelStatus.DOWNLOADED)

    # ------------------------------------------------------------------
    # 槽：下载
    # ------------------------------------------------------------------
    def _start_download(self) -> None:
        """启动选中模型的下载。"""
        model_name = self._current_model_name()
        if model_name is None:
            return

        if self._download_worker is not None and self._download_worker.isRunning():
            QMessageBox.information(
                self, "提示", "已有模型正在下载，请等待当前任务完成。"
            )
            return

        info = self._manager.get_model_info(model_name)
        size_text = self._manager.format_size(info.get("size_mb", 0))
        confirm = QMessageBox.question(
            self,
            "确认下载",
            f"将下载模型「{model_name}」(约 {size_text})，可能需要较长时间。\n"
            "确定继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        # 标记并启动 worker
        self._manager.set_downloading(model_name)

        models_dir = self._manager.get_models_dir()
        worker = ModelDownloadWorker(model_name, models_dir, parent=self)
        worker.download_progress.connect(self._on_download_progress)
        worker.download_completed.connect(self._on_download_completed)
        worker.download_failed.connect(self._on_download_failed)
        worker.status_message.connect(self._on_download_status)
        worker.finished.connect(self._on_worker_finished)
        self._download_worker = worker

        # 显示进度区
        self._progress_download.setValue(0)
        self._label_download_status.setText(f"准备下载 {model_name}...")
        self._group_progress.show()

        worker.start()

        self._refresh_model_list()
        self._update_button_states(model_name)

    def _cancel_download(self) -> None:
        """取消当前下载。"""
        if self._download_worker is None or not self._download_worker.isRunning():
            return

        confirm = QMessageBox.question(
            self,
            "确认取消",
            "确定要取消当前下载吗？已下载的部分文件将保留在本地。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        model_name = self._download_worker.model_name
        self._download_worker.cancel()
        self._label_download_status.setText("正在取消下载...")
        self._btn_cancel_download.setEnabled(False)

        # 等待 worker 结束（最多 3 秒），超时则强制终止
        if not self._download_worker.wait(3000):
            self._download_worker.terminate()
            self._download_worker.wait(1000)

        # 立即清理状态
        self._manager.set_download_finished(model_name)
        self._download_worker = None
        self._label_download_status.setText("下载已取消")
        self._group_progress.hide()
        self._refresh_model_list()
        self._update_button_states(self._current_model_name())

    def _on_download_progress(self, _model_name: str, progress: float) -> None:
        """更新进度条。"""
        value = max(0, min(100, int(progress * 100)))
        self._progress_download.setValue(value)

    def _on_download_status(self, message: str) -> None:
        """更新下载状态文本。"""
        self._label_download_status.setText(message)

    def _on_download_completed(self, model_name: str) -> None:
        """下载完成回调。"""
        self._manager.set_download_finished(model_name)
        self._progress_download.setValue(100)
        self._label_download_status.setText(f"模型「{model_name}」下载完成")

        QMessageBox.information(
            self, "下载完成", f"模型「{model_name}」已下载完成。"
        )

        self._refresh_model_list()
        self._update_button_states(self._current_model_name())
        self.model_changed.emit()

    def _on_download_failed(self, model_name: str, error: str) -> None:
        """下载失败回调。"""
        self._manager.set_download_finished(model_name)
        self._label_download_status.setText(f"下载失败: {error}")

        QMessageBox.critical(
            self, "下载失败", f"模型「{model_name}」下载失败：\n{error}"
        )

        self._refresh_model_list()
        self._update_button_states(self._current_model_name())

    def _on_worker_finished(self) -> None:
        """worker 线程结束统一收尾。"""
        if self._download_worker is not None:
            model_name = self._download_worker.model_name
            # 确保清理下载状态（处理取消的情况）
            self._manager.set_download_finished(model_name)
        self._download_worker = None
        self._group_progress.hide()
        self._refresh_model_list()
        self._update_button_states(self._current_model_name())

    # ------------------------------------------------------------------
    # 槽：删除 / 验证 / 设为默认
    # ------------------------------------------------------------------
    def _delete_model(self) -> None:
        """删除选中的已下载模型。"""
        model_name = self._current_model_name()
        if model_name is None:
            return

        if model_name == self._settings.model_size:
            QMessageBox.warning(
                self,
                "无法删除",
                f"模型「{model_name}」当前为默认模型，请先切换默认模型后再删除。",
            )
            return

        confirm = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除模型「{model_name}」吗？此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        ok, message = self._manager.delete_model(model_name)
        if ok:
            QMessageBox.information(self, "删除成功", message)
            self._refresh_model_list()
            self._update_button_states(self._current_model_name())
            self.model_changed.emit()
        else:
            QMessageBox.critical(self, "删除失败", message)

    def _validate_model(self) -> None:
        """验证选中模型的完整性。"""
        model_name = self._current_model_name()
        if model_name is None:
            return

        ok, message = self._manager.validate_model(model_name)
        if ok:
            QMessageBox.information(
                self, "验证通过", f"模型「{model_name}」: {message}"
            )
        else:
            QMessageBox.warning(
                self, "验证失败", f"模型「{model_name}」: {message}"
            )

    def _set_as_default(self) -> None:
        """将选中的已下载模型设为默认。"""
        model_name = self._current_model_name()
        if model_name is None:
            return

        if self._manager.get_model_status(model_name) != ModelStatus.DOWNLOADED:
            QMessageBox.warning(
                self, "无法设置", "只能将已下载的模型设为默认。"
            )
            return

        if self._settings.model_size == model_name:
            QMessageBox.information(
                self, "提示", f"「{model_name}」已是默认模型。"
            )
            return

        self._settings.model_size = model_name
        QMessageBox.information(
            self, "已更新", f"已将「{model_name}」设为默认模型。"
        )

        self._refresh_model_list()
        self._update_button_states(self._current_model_name())
        self.model_changed.emit()

    # ------------------------------------------------------------------
    # 关闭逻辑
    # ------------------------------------------------------------------
    def closeEvent(self, event) -> None:  # type: ignore[override]
        """关闭对话框时确保后台线程安全退出。"""
        if self._download_worker is not None and self._download_worker.isRunning():
            confirm = QMessageBox.question(
                self,
                "下载进行中",
                "当前有模型正在下载，关闭窗口将取消下载。是否继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirm != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._download_worker.cancel()
            self._download_worker.wait(2000)

        event.accept()
