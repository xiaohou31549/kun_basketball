import os

# Debug mode flag
DEBUG = False  # 生产环境设置为 False

# NBA teams to track
TEAMS = ['湖人', '勇士', '独行侠']

# Base URL for NBA videos
BASE_URL = 'https://www.yoozhibo.net/lanqiu/nba/video-p1.html'

# Days to look back for matches (default to 3 days in debug mode, 1 day in production)
DAYS_TO_LOOK_BACK = 1

# Download directories
NAS_DOWNLOAD_DIR = '/downloads'  # 对应 docker-compose.yml 中的挂载点
LOCAL_DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'downloads')

# Get the appropriate download directory based on debug mode
DOWNLOAD_DIR = LOCAL_DOWNLOAD_DIR if DEBUG else NAS_DOWNLOAD_DIR

# Weibo video quality preference
# 可选值: '1080p', '720p', '480p'
PREFERRED_QUALITY = '480p' if DEBUG else '1080p'

# you-get quality configuration
YOU_GET_QUALITY_ARGS = {
    '1080p': '--format=dash-flv1080',
    '720p': '--format=dash-flv720',
    '480p': '--format=dash-flv480'
}

# Create local video directory if it doesn't exist and in debug mode
if DEBUG and not os.path.exists(LOCAL_DOWNLOAD_DIR):
    os.makedirs(LOCAL_DOWNLOAD_DIR)
