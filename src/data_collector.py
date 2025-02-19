import logging
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from apify_client import ApifyClient
import os
import pandas as pd
import json
import random
import urllib.parse

class RedditDataCollector:
    def __init__(self, config):
        """Initialize with configuration dictionary"""
        # Set up logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger('RedditDataCollector')
        
        # Store config
        self.config = config
        self.retry_delay = 5
        
        # List of user agents to rotate
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
        ]
        
        # Initialize headers with random user agent
        self.headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        # Initialize session and proxy configuration
        self._initialize_session()
        
    def _initialize_session(self):
        """Initialize session with proxy configuration if available"""
        self.logger.info("\n=== Session Initialization ===")
        try:
            # Initialize session
            self.session = requests.Session()
            self.session.headers.update(self.headers)
            
            # Try to get Apify proxy if available
            if 'APIFY_PROXY_PASSWORD' in os.environ:
                proxy_password = os.environ['APIFY_PROXY_PASSWORD']
                proxy_host = os.environ.get('APIFY_PROXY_HOST', 'proxy.apify.com')
                proxy_port = os.environ.get('APIFY_PROXY_PORT', '8000')
                
                # Construct proxy URL with residential group
                proxy_url = f"http://auto:{proxy_password}@{proxy_host}:{proxy_port}"
                
                self.proxies = {
                    'http': proxy_url,
                    'https': proxy_url
                }
                self.session.proxies.update(self.proxies)
                self.logger.info("✅ Session initialized with Apify residential proxy")
            else:
                self.logger.warning("⚠️ No Apify proxy configuration found, proceeding without proxy")
            
        except Exception as e:
            self.logger.error(f"❌ Session initialization failed: {e}")
            self.logger.warning("⚠️ Continuing without proxy configuration")
            
    def collect_data(self):
        """Collect data using direct JSON endpoints with improved error handling and retries"""
        subreddits = self.config.get('subreddits', ['wallstreetbets', 'stocks', 'investing'])
        timeframe = self.config.get('timeframe', 'week')
        post_limit = self.config.get('postLimit', 100)
        
        all_posts = []
        for subreddit in subreddits:
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    # Rotate user agent
                    self.session.headers.update({'User-Agent': random.choice(self.user_agents)})
                    
                    # Use old.reddit.com for better compatibility
                    url = f"https://old.reddit.com/r/{subreddit}/top.json?t={timeframe}&limit={post_limit}"
                    self.logger.info(f"Fetching data from: {url}")
                    
                    response = self.session.get(url, timeout=30)
                    self.logger.debug(f"Response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        posts = data['data']['children']
                        
                        for post in posts:
                            post_data = post['data']
                            all_posts.append({
                                'title': post_data.get('title', ''),
                                'selftext': post_data.get('selftext', ''),
                                'score': post_data.get('score', 0),
                                'created_utc': datetime.fromtimestamp(post_data.get('created_utc', 0)),
                                'comments': post_data.get('num_comments', 0),
                                'subreddit': post_data.get('subreddit', ''),
                                'url': post_data.get('url', ''),
                                'author': post_data.get('author', '[deleted]')
                            })
                        
                        self.logger.info(f"Successfully collected {len(posts)} posts from r/{subreddit}")
                        break  # Success, exit retry loop
                        
                    elif response.status_code == 429:  # Too Many Requests
                        retry_count += 1
                        wait_time = int(response.headers.get('Retry-After', self.retry_delay))
                        self.logger.warning(f"Rate limited. Waiting {wait_time} seconds before retry {retry_count}/{max_retries}")
                        time.sleep(wait_time)
                        
                    else:
                        self.logger.error(f"Error accessing r/{subreddit}: Status code {response.status_code}")
                        retry_count += 1
                        time.sleep(self.retry_delay)
                        
                except Exception as e:
                    self.logger.error(f"Error collecting data from r/{subreddit}: {str(e)}")
                    retry_count += 1
                    time.sleep(self.retry_delay)
                    continue
                
            # Respect rate limits between subreddits
            time.sleep(2)
                
        return pd.DataFrame(all_posts) if all_posts else pd.DataFrame()