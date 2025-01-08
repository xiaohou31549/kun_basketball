import os
import requests
import logging
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import random
import re
from tqdm import tqdm

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except (ImportError, Exception) as e:
    SELENIUM_AVAILABLE = False
    print(f"Selenium not available, falling back to requests mode: {str(e)}")

from nba_downloader.config import TEAMS, BASE_URL, DOWNLOAD_DIR, PREFERRED_QUALITY, DEBUG, YOU_GET_QUALITY_ARGS
from nba_downloader.video_downloader import VideoDownloader

# 设置日志
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(DOWNLOAD_DIR, 'nba_downloader.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NBAVideoDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.use_selenium = True
        self.driver = None
        self.video_downloader = VideoDownloader(DOWNLOAD_DIR, YOU_GET_QUALITY_ARGS)
        self.init_selenium()

    def init_selenium(self):
        """初始化Selenium"""
        try:
            chrome_options = Options()
            if not DEBUG:
                chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument(f'user-agent={self.session.headers["User-Agent"]}')

            # 禁用webdriver特征
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                '''
            })
            logger.info("Selenium initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Selenium: {str(e)}")
            self.use_selenium = False

    def __del__(self):
        """清理资源"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

    def get_yesterday_dates(self):
        """获取前一天的日期，返回多种格式以便匹配"""
        yesterday = datetime.now() - timedelta(days=1)
        # 返回多种可能的日期格式
        dates = {
            'standard': yesterday.strftime('%m月%d日'),  # 01月05日，用于匹配
            'display': yesterday.strftime('%-m月%-d号'),  # 1月5号，用于显示
            'numeric': yesterday.strftime('%m%d')  # 0105
        }
        logger.debug(f"Generated yesterday dates: {dates}")
        return dates

    def format_date(self, date_text):
        """格式化日期文本，去掉前导零"""
        # 使用正则表达式匹配日期格式
        match = re.match(r'(\d{1,2})月(\d{1,2})日', date_text)
        if match:
            month, day = match.groups()
            # 将字符串转为整数去掉前导零，再转回字符串
            return f"{int(month)}月{int(day)}号"
        return date_text

    def extract_date_from_title(self, title):
        """从标题中提取日期"""
        try:
            # 匹配格式：01月05日 或 1月5日
            date_match = re.search(r'(\d{1,2})月(\d{1,2})日', title)
            if date_match:
                month, day = date_match.groups()
                # 保持带前导零的格式用于匹配
                return f"{int(month):02d}月{int(day):02d}日"
            return None
        except Exception as e:
            logger.error(f"Error extracting date from title: {str(e)}")
            return None

    def create_match_directory(self, date_text, title):
        """创建比赛目录"""
        # 从标题中提取球队信息
        teams = []
        for team in TEAMS:
            if team in title:
                teams.append(team)
        
        if len(teams) >= 2:
            teams_str = f"{teams[0]}vs{teams[1]}"
        else:
            teams_str = title
            
        # 创建简洁的目录名: 1月5号灰熊vs勇士
        formatted_date = self.format_date(date_text)  # 格式化日期，去掉前导零
        
        # 确保所有字符都是合法的 ASCII 或 UTF-8
        dir_name = f"{formatted_date}{teams_str}"
        try:
            # 尝试将字符串编码为 ASCII（移除所有非 ASCII 字符）
            dir_name_ascii = dir_name.encode('ascii', 'ignore').decode('ascii')
            if dir_name_ascii.strip():  # 如果转换后还有内容
                dir_name = dir_name_ascii
            else:
                # 如果转换后为空，使用 UTF-8 编码
                dir_name = dir_name.encode('utf-8').decode('utf-8')
        except UnicodeError:
            # 如果出现编码错误，使用 UTF-8
            dir_name = dir_name.encode('utf-8').decode('utf-8')
            
        # 移除非法字符
        dir_name = re.sub(r'[<>:"/\\|?*]', '', dir_name)
        
        # 记录最终的目录名
        logger.debug(f"Created directory name: {dir_name}, encoding: {dir_name.encode()}")
        
        full_path = os.path.join(DOWNLOAD_DIR, dir_name)
        
        # 确保目录存在
        if not os.path.exists(full_path):
            os.makedirs(full_path)
            # 设置目录权限为 755
            os.chmod(full_path, 0o755)
            logger.debug(f"Created directory: {full_path}")
            
        return full_path

    def is_yesterday_match(self, date_text):
        """检查是否是昨天的比赛"""
        if not date_text:
            return False
            
        yesterday_dates = self.get_yesterday_dates()
        logger.debug(f"Comparing date_text '{date_text}' with yesterday_dates {yesterday_dates}")
        
        # 标准化日期格式进行比较
        try:
            match = re.match(r'(\d{1,2})月(\d{1,2})日', date_text)
            if match:
                month, day = match.groups()
                normalized_date = f"{int(month):02d}月{int(day):02d}日"
                return normalized_date == yesterday_dates['standard']
        except Exception as e:
            logger.error(f"Error comparing dates: {str(e)}")
            return False
            
        return False

    def is_team_match(self, match_title):
        """检查比赛是否包含关注的球队"""
        return any(team in match_title for team in TEAMS)

    def get_page_content(self, url, use_selenium=False):
        """获取页面内容"""
        logger.info(f"Fetching URL: {url}")
        try:
            if use_selenium and self.use_selenium:
                self.driver.get(url)
                time.sleep(random.uniform(2, 3))  # 等待页面加载
                content = self.driver.page_source
                logger.debug("Page fetched using Selenium")
            else:
                response = self.session.get(url)
                response.raise_for_status()
                content = response.text
                logger.debug("Page fetched using requests")

            if DEBUG:
                logger.debug(f"Content length: {len(content)}")
            return content
        except Exception as e:
            logger.error(f"Error fetching page {url}: {str(e)}")
            return None

    def get_video_url(self, detail_url):
        """从详情页获取视频URL"""
        try:
            content = self.get_page_content(detail_url)
            if not content:
                return None
                
            soup = BeautifulSoup(content, 'html.parser')
            video_links = []
            
            # 查找微博链接
            for a in soup.select('#lx li.cd a, #jj li.cd a'):
                if '微博' in a.text:
                    quarter = None
                    for q in ['第一节', '第二节', '第三节', '第四节']:
                        if q in a.text:
                            quarter = q
                            break
                    
                    weibo_url = a['href']
                    logger.info(f"Found Weibo video: {weibo_url}")
                    
                    video_links.append({
                        'type': 'weibo',
                        'url': weibo_url,
                        'text': a.text,
                        'quarter': quarter,
                        'priority': 2 if '国语' in a.text else 1
                    })
            
            # 按优先级排序视频链接（微博国语 > 微博普通）
            video_links.sort(key=lambda x: (-x['priority'], x['quarter'] or ''))
            return video_links
            
        except Exception as e:
            logger.error(f"Error getting video URL from detail page: {str(e)}")
            return None

    def convert_quarter_name(self, quarter_text):
        """将中文节数转换为数字"""
        quarter_map = {
            '第一节': '1',
            '第二节': '2',
            '第三节': '3',
            '第四节': '4',
            '加时': 'OT'
        }
        return quarter_map.get(quarter_text, quarter_text)

    def process_match(self, match):
        """处理单场比赛"""
        logger.info(f"Processing match: {match['title']}")
        
        # 创建比赛目录
        match_dir = self.create_match_directory(match['date'], match['title'])
        
        # 获取视频链接
        video_links = self.get_video_url(match['url'])
        if not video_links:
            logger.error("Failed to get video links")
            return False

        # 提取球队信息用于文件名
        teams = []
        for team in TEAMS:
            if team in match['title']:
                teams.append(team)
        
        base_filename = f"{teams[0]}vs{teams[1]}" if len(teams) >= 2 else match['title']
        
        # 确保球队名称使用正确的编码
        try:
            base_filename = base_filename.encode('utf-8').decode('utf-8')
        except UnicodeError:
            logger.warning(f"Error encoding team names: {base_filename}")
        
        # 下载视频
        success = True
        for video_info in video_links:
            if '节' in video_info.get('text', ''):
                # 将中文节数转换为数字: 灰熊vs勇士_第1节
                quarter = re.search(r'第[一二三四]节|加时', video_info['text'])
                if quarter:
                    quarter_num = self.convert_quarter_name(quarter.group())
                    filename = f"{base_filename}_第{quarter_num}节"
                else:
                    filename = f"{base_filename}_{video_info['text']}"
            else:
                filename = base_filename

            try:
                # 确保文件名使用正确的编码
                filename = filename.encode('utf-8').decode('utf-8')
            except UnicodeError:
                logger.warning(f"Error encoding filename: {filename}")
            
            # 移除非法字符
            filename = re.sub(r'[<>:"/\\|?*]', '', filename)
            
            # 记录文件名编码信息
            logger.debug(f"Video filename: {filename}, encoding: {filename.encode()}")
            
            video_path = os.path.join(match_dir, filename)
            
            # 如果文件已存在且大小大于 1MB，跳过下载
            if os.path.exists(video_path) and os.path.getsize(video_path) > 1024 * 1024:
                logger.info(f"Video already exists: {video_path}")
                continue
            
            # 下载视频
            success = self.video_downloader.download(video_info, match_dir, filename, PREFERRED_QUALITY)
            if success:
                # 设置文件权限为 644
                os.chmod(video_path, 0o644)
                logger.info(f"Successfully downloaded: {video_path}")
            else:
                logger.error(f"Failed to download: {video_path}")
            
        return success

    def get_matches(self):
        """获取比赛列表"""
        content = self.get_page_content(BASE_URL, use_selenium=True)
        if not content:
            return []
            
        soup = BeautifulSoup(content, 'html.parser')
        matches = []
        
        # 获取昨天的日期
        yesterday_dates = self.get_yesterday_dates()
        logger.info(f"Looking for matches from dates: {yesterday_dates}")
        
        # 保存页面内容用于调试
        if DEBUG:
            debug_file = os.path.join(DOWNLOAD_DIR, 'debug_page.html')
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.debug(f"Saved page content to {debug_file}")
        
        # 查找所有比赛
        for match_item in soup.select('.wrap-body li.c'):
            try:
                # 获取日期
                date_elem = match_item.select_one('em')
                if not date_elem:
                    logger.debug("No date element found")
                    continue
                date_text = date_elem.text.strip()
                logger.debug(f"Found date: {date_text}")
                
                # 获取标题和链接
                link_elem = match_item.select_one('a[href*="/video-"]')
                if not link_elem:
                    logger.debug("No link element found")
                    continue
                    
                title = link_elem.text.strip()
                logger.debug(f"Found title: {title}")
                
                # 从标题中提取日期和球队
                title_parts = title.split(' ')
                if len(title_parts) < 4:  # 确保标题格式正确
                    continue
                    
                match_date = title_parts[0]  # 例如："01月01日"
                logger.debug(f"Extracted date from title: {match_date}")
                
                # 提取球队名称
                teams = []
                for team in TEAMS:
                    if team in title:
                        teams.append(team)
                
                # 如果找到了两支球队，创建一个更简洁的标题
                if len(teams) >= 2:
                    simplified_title = f"{teams[0]}vs{teams[1]}"
                else:
                    # 尝试从标题中提取球队名称（通常在"vs"周围）
                    vs_index = title.find('vs')
                    if vs_index != -1:
                        # 在"vs"前后查找空格来提取球队名称
                        before_vs = title[:vs_index].strip().split(' ')[-1]
                        after_vs = title[vs_index+2:].strip().split(' ')[0]
                        simplified_title = f"{before_vs}vs{after_vs}"
                    else:
                        simplified_title = title
                
                # 检查是否是昨天的比赛和关注的球队
                is_yesterday = self.is_yesterday_match(match_date)
                is_team = self.is_team_match(title)
                logger.debug(f"Is yesterday match: {is_yesterday}, Is team match: {is_team}")
                
                if is_yesterday and is_team:
                    detail_url = urljoin(BASE_URL, link_elem['href'])
                    matches.append({
                        'title': simplified_title,
                        'url': detail_url,
                        'date': match_date
                    })
                    logger.info(f"Found match: {simplified_title} ({match_date})")
            
            except Exception as e:
                logger.error(f"Error parsing match item: {str(e)}")
                continue
        
        logger.info(f"Total matches found: {len(matches)}")
        return matches

    def run(self):
        """运行下载器"""
        try:
            logger.info("Starting NBA video downloader")
            logger.info(f"Base URL: {BASE_URL}")
            logger.info(f"Download directory: {DOWNLOAD_DIR}")
            logger.info(f"Teams to track: {TEAMS}")

            # 获取比赛列表
            matches = self.get_matches()
            if not matches:
                logger.info("No matches found")
                return

            total_matches = len(matches)
            successful_downloads = 0

            for match in matches:
                if self.process_match(match):
                    successful_downloads += 1

            # 添加总结日志
            logger.info("=== 下载任务总结 ===")
            logger.info(f"今日符合要求的比赛数量: {total_matches}")
            logger.info(f"成功下载的比赛数量: {successful_downloads}")
            logger.info(f"下载成功率: {(successful_downloads/total_matches*100):.1f}% 如果成功率较低，请检查日志中的详细错误信息")
            logger.info("================")

        except Exception as e:
            logger.error(f"Error running downloader: {str(e)}")
            if DEBUG:
                raise

def main():
    """Entry point for the application."""
    downloader = NBAVideoDownloader()
    downloader.run()

if __name__ == '__main__':
    main()
