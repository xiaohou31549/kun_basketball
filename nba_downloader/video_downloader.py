import os
import logging
import subprocess
import sys
import time
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class VideoDownloader:
    def __init__(self, download_dir: str, quality_config: Dict[str, str], max_retries: int = 3, retry_delay: int = 5):
        self.download_dir = download_dir
        self.quality_config = quality_config
        self.you_get_path = sys.executable
        self.max_retries = max_retries  # 最大重试次数
        self.retry_delay = retry_delay  # 重试间隔（秒）

    def download(self, video_info: Dict[str, Any], output_dir: str, filename: str, quality: str) -> bool:
        retries = 0
        while retries < self.max_retries:
            try:
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)

                if retries > 0:
                    logger.info(f"第 {retries} 次重试下载: {filename}")
                    time.sleep(self.retry_delay)  # 重试前等待
                else:
                    logger.info(f"开始下载: {filename}")
                
                if video_info['type'] != 'weibo':
                    logger.error(f"不支持的视频类型: {video_info['type']}")
                    return False

                # 构建下载命令
                cmd = [
                    self.you_get_path,
                    '-m', 'you_get',
                    '-o', output_dir,
                    '-O', filename
                ]
                
                # 添加清晰度参数
                quality_arg = self.quality_config.get(quality, '')
                if quality_arg:
                    cmd.append(quality_arg)
                
                cmd.append(video_info['url'])
                
                # 使用 Popen 来实时获取输出
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    bufsize=1
                )

                last_log_time = 0
                downloading = False

                while True:
                    output = process.stdout.readline()
                    if output == '' and process.poll() is not None:
                        break
                    
                    output = output.strip()
                    if output:
                        current_time = time.time()
                        
                        # 检测下载开始
                        if 'Downloading' in output:
                            downloading = True
                            last_log_time = current_time
                            logger.info(f"{filename} - {output}")
                            continue
                        
                        # 只在下载过程中每15秒输出一次进度
                        if downloading and current_time - last_log_time >= 15:
                            # 只输出包含进度信息的行
                            if '%' in output:
                                logger.info(f"{filename} - {output}")
                                last_log_time = current_time

                # 检查下载结果
                return_code = process.poll()
                if return_code == 0:
                    logger.info(f"下载完成: {filename}")
                    return True
                else:
                    logger.error(f"下载失败 {filename}, 错误码: {return_code}")
                    retries += 1
                    continue
                
            except subprocess.CalledProcessError as e:
                logger.error(f"下载出错: {str(e)}")
                retries += 1
                continue
                
            except Exception as e:
                logger.error(f"下载异常: {str(e)}")
                retries += 1
                continue

        logger.error(f"达到最大重试次数 ({self.max_retries})，放弃下载: {filename}")
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
