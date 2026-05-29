# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all, collect_data_files

# 收集 faster-whisper 和 ctranslate2 的所有依赖
faster_whisper_datas, faster_whisper_binaries, faster_whisper_hiddenimports = collect_all('faster_whisper')
ctranslate2_datas, ctranslate2_binaries, ctranslate2_hiddenimports = collect_all('ctranslate2')

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
    binaries=faster_whisper_binaries + ctranslate2_binaries + [('ffmpeg/ffmpeg.exe', 'ffmpeg')],
    datas=faster_whisper_datas + ctranslate2_datas + model_datas,
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
        'matplotlib', 'scipy', 'IPython', 'notebook',
        'tkinter', 'test', 'unittest',
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
