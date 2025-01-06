import os
import logging
import subprocess
import sys
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class VideoDownloader:
    def __init__(self, download_dir: str, quality_config: Dict[str, str]):
        """
        初始化视频下载器
        :param download_dir: 下载目录
        :param quality_config: 清晰度配置，例如 {'1080p': '--format=dash-flv1080'}
        """
        self.download_dir = download_dir
        self.quality_config = quality_config
        self.you_get_path = os.path.join(os.path.dirname(sys.executable), 'you-get')

    def download(self, video_info: Dict[str, Any], output_dir: str, filename: str, quality: str) -> bool:
        """
        下载视频
        :param video_info: 视频信息，包含 url 和 type
        :param output_dir: 输出目录
        :param filename: 输出文件名（不含扩展名）
        :param quality: 视频清晰度
        :return: 是否下载成功
        """
        try:
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            logger.info(f"Downloading to: {os.path.join(output_dir, filename)}.mp4")
            logger.info(f"Video URL: {video_info['url']}")
            
            if video_info['type'] != 'weibo':
                logger.error(f"Unsupported video type: {video_info['type']}")
                return False

            logger.info(f"Using you-get from: {self.you_get_path}")
            
            # 构建下载命令
            cmd = [
                self.you_get_path,
                '--debug',
                '-o', output_dir,
                '-O', filename
            ]
            
            # 添加清晰度参数
            quality_arg = self.quality_config.get(quality, '')
            if quality_arg:
                cmd.append(quality_arg)
            
            cmd.append(video_info['url'])
            
            logger.info(f"Running command: {' '.join(cmd)}")
            
            # 执行下载
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info(f"you-get stdout:\n{result.stdout}")
            if result.stderr:
                logger.debug(f"you-get stderr:\n{result.stderr}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running you-get: {str(e)}")
            if e.stdout:
                logger.error(f"you-get stdout:\n{e.stdout}")
            if e.stderr:
                logger.error(f"you-get stderr:\n{e.stderr}")
            return False
            
        except Exception as e:
            logger.error(f"Error downloading video: {str(e)}")
            return False

    def download_videos(self, videos: list, output_dir: str, base_filename: str, quality: str) -> bool:
        """
        下载一组视频
        :param videos: 视频列表
        :param output_dir: 输出目录
        :param base_filename: 基础文件名
        :param quality: 视频清晰度
        :return: 是否全部下载成功
        """
        success = True
        for video_info in videos:
            # 处理分节信息
            quarter_str = f"_{video_info['quarter']}" if video_info.get('quarter') else ""
            filename = f"{base_filename}{quarter_str}"
            
            if not self.download(video_info, output_dir, filename, quality):
                logger.error(f"Failed to download video: {video_info.get('text', video_info['url'])}")
                success = False
                
        return success
