# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

# 精确收集 faster-whisper 和 ctranslate2 的依赖（避免 collect_all 引入冗余）
faster_whisper_datas = collect_data_files('faster_whisper')
faster_whisper_binaries = collect_dynamic_libs('faster_whisper')
faster_whisper_hiddenimports = ['faster_whisper']

ctranslate2_datas = collect_data_files('ctranslate2')
ctranslate2_binaries = collect_dynamic_libs('ctranslate2')
ctranslate2_hiddenimports = ['ctranslate2']

# 排除 CUDA 相关的大体积库（GPU 用户系统自带 CUDA 环境）
_cuda_keywords = ('cudnn', 'cublas', 'cufft', 'curand', 'cusparse', 'cusolver', 'nvinfer', 'nvrtc', 'cudart')
ctranslate2_binaries = [
    (src, dst) for src, dst in ctranslate2_binaries
    if not any(kw in os.path.basename(src).lower() for kw in _cuda_keywords)
]

# 检查并包含本地模型
model_datas = []
models_dir = 'models'
if os.path.isdir(models_dir):
    for model_name in os.listdir(models_dir):
        model_path = os.path.join(models_dir, model_name)
        if os.path.isdir(model_path) and os.path.isfile(os.path.join(model_path, 'model.bin')):
            model_datas.append((model_path, os.path.join('models', model_name)))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=faster_whisper_binaries + ctranslate2_binaries,
    datas=faster_whisper_datas + ctranslate2_datas + model_datas + [('resources/icons/app.ico', 'resources/icons')],
    hiddenimports=[
        'faster_whisper',
        'ctranslate2',
        'huggingface_hub',
        'tokenizers',
        'PySide6',
    ] + faster_whisper_hiddenimports + ctranslate2_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['runtime_hook.py'],
    excludes=[
        # 无关 Python 包
        'matplotlib', 'scipy', 'IPython', 'notebook',
        'tkinter', 'test', 'unittest',
        'numpy.testing', 'numpy.distutils',
        'setuptools', 'pkg_resources',
        # VAD 已禁用，无需 onnxruntime
        'onnxruntime',
        # 不需要的 PySide6 模块
        'PySide6.QtWebEngine', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
        'PySide6.QtWebChannel',
        'PySide6.Qt3DCore', 'PySide6.Qt3DRender', 'PySide6.Qt3DInput',
        'PySide6.Qt3DLogic', 'PySide6.Qt3DAnimation', 'PySide6.Qt3DExtras',
        'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets',
        'PySide6.QtNetwork',
        'PySide6.QtSql',
        'PySide6.QtSvg',
        'PySide6.QtBluetooth', 'PySide6.QtNfc',
        'PySide6.QtSensors', 'PySide6.QtSerialPort',
        'PySide6.QtPositioning', 'PySide6.QtLocation',
        'PySide6.QtQuick', 'PySide6.QtQuickWidgets', 'PySide6.QtQml',
        'PySide6.QtQuick3D', 'PySide6.QtQuickControls2',
        'PySide6.QtDesigner', 'PySide6.QtHelp',
        'PySide6.QtPdf', 'PySide6.QtPdfWidgets',
        'PySide6.QtCharts', 'PySide6.QtDataVisualization',
        'PySide6.QtOpenGL', 'PySide6.QtOpenGLWidgets',
        'PySide6.QtTest',
        'PySide6.QtRemoteObjects', 'PySide6.QtScxml',
        'PySide6.QtStateMachine', 'PySide6.QtHttpServer',
        'PySide6.QtSvgWidgets',
        'PySide6.QtPrintSupport',
        'PySide6.QtConcurrent',
        'PySide6.QtDBus',
        'PySide6.QtWebSockets',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='V2T',
    icon='resources/icons/app.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='V2T',
)
