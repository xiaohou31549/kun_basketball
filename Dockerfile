# 使用中科大镜像源的 Python 镜像
FROM python:3.9-slim

# 设置非交互式安装
ENV DEBIAN_FRONTEND=noninteractive

# 设置工作目录
WORKDIR /app

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 使用清华大学源
RUN echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bullseye main contrib non-free\n\
deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bullseye-updates main contrib non-free\n\
deb https://mirrors.tuna.tsinghua.edu.cn/debian-security bullseye-security main contrib non-free" > /etc/apt/sources.list

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    tzdata \
    gcc \
    python3-dev \
    cron \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 创建媒体用户
RUN useradd -u 1026 -g 100 -m -s /bin/bash media

# 设置 pip 源为清华源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip config set install.trusted-host pypi.tuna.tsinghua.edu.cn

# 设置 Chrome 相关环境变量
ENV CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver

# 复制项目文件
COPY . /app/

# 安装项目依赖
RUN pip install -e .

# 创建下载目录并设置权限
RUN mkdir -p /downloads && \
    chown media:users /downloads && \
    chmod 755 /downloads

# 设置环境变量
ENV PYTHONUNBUFFERED=1

# 设置工作目录所有权
RUN chown -R media:users /app

# 启动命令
CMD ["python", "-m", "nba_downloader.nba_video_downloader"]
