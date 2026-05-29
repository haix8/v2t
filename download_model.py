"""提前下载 Whisper 模型到项目 models/ 目录"""
import os
import sys

def download_model(model_size: str = "large-v3"):
    """下载指定大小的 faster-whisper 模型到 models/ 目录"""
    from huggingface_hub import snapshot_download

    models_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')
    model_dir_name = f"faster-whisper-{model_size}"
    local_dir = os.path.join(models_dir, model_dir_name)
    os.makedirs(local_dir, exist_ok=True)

    repo_id = f"Systran/faster-whisper-{model_size}"
    print(f"正在下载模型 {repo_id} 到 {local_dir} ...")
    print("(首次下载可能需要较长时间，请耐心等待)")

    snapshot_download(
        repo_id=repo_id,
        local_dir=local_dir,
        local_dir_use_symlinks=False,
    )
    print(f"模型下载完成: {local_dir}")

if __name__ == "__main__":
    # 支持命令行参数指定模型大小
    model = sys.argv[1] if len(sys.argv) > 1 else "large-v3"
    print(f"目标模型: {model}")
    print("可选模型: tiny, base, small, medium, large-v3")
    print()
    download_model(model)