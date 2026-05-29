"""PyInstaller runtime hook - 修复 Windows 无控制台时 stdout/stderr 为 None 的问题"""
import sys
import os

if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')
