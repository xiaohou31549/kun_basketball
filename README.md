# NBA Video Downloader

自动下载 NBA 比赛视频的工具，支持群晖 NAS 部署。

## 功能特点

- 自动获取昨日 NBA 比赛视频
- 支持多个视频源（微博、腾讯视频）
- 支持配置关注的球队
- 支持多种视频清晰度（1080p、720p、480p）
- Docker 容器化部署
- 自动定时下载

## 快速开始

### 本地开发

1. 克隆仓库
   ```bash
   git clone https://github.com/yourusername/nba-downloader.git
   cd nba-downloader
   ```

2. 创建虚拟环境
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 或
   .\venv\Scripts\activate  # Windows
   ```

3. 安装依赖
   ```bash
   pip install -e .
   ```

4. 配置
   ```bash
   cp config.py config.local.py
   # 编辑 config.local.py 设置你的配置
   ```

5. 运行
   ```bash
   python -m nba_downloader.nba_video_downloader
   ```

### Docker 部署

详见 [部署文档](docs/deployment.md)

## 配置说明

1. 复制配置文件模板：
   ```bash
   cp nba_downloader/config.py.example nba_downloader/config.py
   ```

2. 编辑 `nba_downloader/config.py` 配置以下选项：
   - `TEAMS`: 要关注的球队列表
   - `DOWNLOAD_DIR`: 视频保存目录
   - `PREFERRED_QUALITY`: 视频清晰度
   - `DEBUG`: 调试模式开关

## 开发指南

1. Fork 本仓库
2. 创建功能分支
3. 提交代码
4. 创建 Pull Request

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件
