## 这是一个音视频提取文字的工具

现有的bug
- 开始转录后，取消功能
- 使用未下载的模型时，下载模型会报错
- 打包应该把预下载好的模型带进打包程序里




## 安装使用
- pip install -r requirements.txt
- python main.py

## 预先下载模型
- python download_model.py large-v3 # 或 medium、small 等
