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

from .config import TEAMS, BASE_URL, DOWNLOAD_DIR, PREFERRED_QUALITY, DEBUG, YOU_GET_QUALITY_ARGS
from .video_downloader import VideoDownloader

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
            'standard': yesterday.strftime('%m月%d日'),  # 01月01日
            'no_leading_zeros': yesterday.strftime('%-m月%-d日'),  # 1月1日
            'numeric': yesterday.strftime('%m%d')  # 0101
        }
        logger.debug(f"Generated yesterday dates: {dates}")
        return dates

    def extract_date_from_title(self, title):
        """从标题中提取日期"""
        try:
            # 移除可能的空格
            title = title.strip()
            
            # 标题格式是 "MM月DD日 NBA常规赛 ..."
            if not title:
                return None
                
            # 提取日期部分 (在第一个空格之前)
            date_part = title.split(' ')[0]
            
            # 验证日期格式
            if not ('月' in date_part and '日' in date_part):
                return None
                
            return date_part
            
        except Exception as e:
            logger.error(f"Error extracting date from title: {str(e)}")
            return None

    def is_yesterday_match(self, date_text, yesterday_dates):
        """检查日期是否是昨天的比赛"""
        if not date_text:
            return False
            
        logger.debug(f"Comparing date_text '{date_text}' with yesterday_dates {yesterday_dates}")
        # 检查所有可能的日期格式
        is_match = any(date_text == date for date in yesterday_dates.values())
        logger.debug(f"Date match result: {is_match}")
        return is_match

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
            
            # 1. 先查找微博链接
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
            
            # 2. 如果没有微博链接或者同时查找QQ国语视频
            for a in soup.select('#lx li.cd a'):
                if 'QQ' in a.text and '国语' in a.text:
                    quarter = None
                    for q in ['第一节', '第二节', '第三节', '第四节']:
                        if q in a.text:
                            quarter = q
                            break
                    
                    qq_url = a['href']
                    logger.info(f"Found QQ video: {qq_url}")
                    
                    video_links.append({
                        'type': 'qq',
                        'url': qq_url,
                        'text': a.text,
                        'quarter': quarter,
                        'priority': 1
                    })
            
            # 按优先级排序视频链接（微博国语 > 微博普通 > QQ国语）
            video_links.sort(key=lambda x: (-x['priority'], x['quarter'] or ''))
            return video_links
            
        except Exception as e:
            logger.error(f"Error getting video URL from detail page: {str(e)}")
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
            
        # 创建简洁的目录名
        dir_name = f"{date_text}_{teams_str}"
        dir_name = re.sub(r'[<>:"/\\|?*]', '_', dir_name)
        return os.path.join(DOWNLOAD_DIR, dir_name)

    def process_match(self, match):
        """处理单场比赛"""
        logger.info(f"Processing match: {match['title']}")
        
        # 创建比赛目录
        match_dir = self.create_match_directory(match['date'], match['title'])
        
        # 获取视频链接
        video_links = self.get_video_url(match['url'])
        if not video_links:
            logger.error(f"Failed to get video URL for match: {match['title']}")
            return False
            
        # 下载视频
        return self.video_downloader.download_videos(
            videos=video_links,
            output_dir=match_dir,
            base_filename=match['title'],
            quality=PREFERRED_QUALITY
        )

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
                is_yesterday = self.is_yesterday_match(match_date, yesterday_dates)
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
        logger.info("Starting NBA video downloader")
        logger.info(f"Base URL: {BASE_URL}")
        logger.info(f"Download directory: {DOWNLOAD_DIR}")
        logger.info(f"Teams to track: {TEAMS}")

        # 获取比赛列表
        matches = self.get_matches()
        if not matches:
            logger.info("No matches found for yesterday")
            return

        logger.info(f"Found {len(matches)} matches to download")

        # 下载每场比赛的视频
        for match in matches:
            if not self.process_match(match):
                logger.error(f"Failed to process match: {match['title']}")

def main():
    """Entry point for the application."""
    downloader = NBAVideoDownloader()
    downloader.run()

if __name__ == '__main__':
    main()
