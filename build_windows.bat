@echo off
chcp 65001 >nul
echo ========================================
echo   V2T - 音视频转文字 Windows 打包工具
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

REM 创建虚拟环境（如果不存在）
if not exist "venv" (
    echo [1/4] 创建虚拟环境...
    python -m venv venv
)

REM 激活虚拟环境
echo [2/4] 激活虚拟环境...
call venv\Scripts\activate.bat

REM 安装依赖
echo [3/4] 安装依赖（首次可能较慢）...
pip install -r requirements.txt -q
pip install pyinstaller -q

REM 检查 ffmpeg
if not exist "ffmpeg\ffmpeg.exe" (
    echo.
    echo [提示] 未找到 ffmpeg\ffmpeg.exe
    echo 请从以下地址下载 ffmpeg 并将 ffmpeg.exe 放入项目的 ffmpeg\ 目录:
    echo https://github.com/BtbN/FFmpeg-Builds/releases
    echo (下载 ffmpeg-master-latest-win64-gpl.zip，解压后将 bin\ffmpeg.exe 复制到 ffmpeg\ 目录)
    echo.
    mkdir ffmpeg 2>nul
    pause
    if not exist "ffmpeg\ffmpeg.exe" (
        echo [错误] 仍未找到 ffmpeg\ffmpeg.exe，无法继续打包
        pause
        exit /b 1
    )
)

REM 检查模型（如已手动放置则自动打包，否则跳过）
echo.
echo [检查模型]...
if exist "models\faster-whisper-large-v3\model.bin" (
    echo 已找到预置模型: models\faster-whisper-large-v3，将一起打包
) else (
    echo 未找到预置模型，跳过模型打包（用户首次运行时将自动下载）
    echo 如需预置模型，请先运行: python download_model.py large-v3
    echo.
)

REM 执行打包
echo [4/4] 开始打包...
echo.
pyinstaller build.spec --clean --noconfirm

echo.
if exist "dist\V2T" (
    echo ========================================
    echo   打包成功！
    echo   输出目录: dist\V2T\
    echo   运行程序: dist\V2T\V2T.exe
    echo ========================================
) else (
    echo [错误] 打包失败，请检查上方错误信息
)

echo.
pause
