import logging
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import os
import pandas as pd
import json
import random
import urllib.parse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from apify_client import ApifyClient
from apify import Actor

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
        self.max_retries = 3
        
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
            'Accept': 'application/json,text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
        
        # Initialize session with retries
        self._initialize_session()
        
    async def _initialize_session(self):
        """Initialize session with proxy configuration and retries"""
        self.logger.info("\n=== Session Initialization ===")
        try:
            self.session = requests.Session()
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[403, 429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self.session.mount("http://", adapter)
            self.session.mount("https://", adapter)
            self.headers.update({
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'DNT': '1',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
            })
            self.session.headers.update(self.headers)
            actor_input = await Actor.get_input() or {}
            proxy_settings = actor_input.get('proxyConfiguration')
            proxy_configuration = await Actor.create_proxy_configuration(actor_proxy_input=proxy_settings)
            if proxy_configuration:
                proxy_url = await proxy_configuration.new_url()
                self.proxies = {
                    'http': proxy_url,
                    'https': proxy_url
                }
                self.session.proxies.update(self.proxies)
                self.logger.info("✅ Session initialized with Apify proxy configuration")
                self._test_proxy_connection()
            else:
                raise Exception("Failed to create proxy configuration")
        except Exception as e:
            self.logger.error(f"❌ Session initialization failed: {e}")
            raise  # Re-raise the exception to handle it in the calling code
    
    def _test_proxy_connection(self):
        """Test proxy connection with a simple request"""
        try:
            test_url = "https://httpbin.org/ip"
            response = self.session.get(test_url, timeout=10)
            if response.status_code == 200:
                self.logger.info(f"✅ Proxy connection test successful: {response.json()}")
            else:
                self.logger.warning(f"⚠️ Proxy test returned status code: {response.status_code}")
        except Exception as e:
            self.logger.error(f"❌ Proxy connection test failed: {e}")
            
    def _make_request(self, url, retries=3):
        """Make a request with automatic retry and proxy rotation"""
        for attempt in range(retries):
            try:
                # Rotate user agent
                self.session.headers.update({'User-Agent': random.choice(self.user_agents)})
                
                # Make request with shorter timeout
                response = self.session.get(url, timeout=15)
                
                if response.status_code == 200:
                    return response
                elif response.status_code == 429:
                    wait_time = int(response.headers.get('Retry-After', self.retry_delay))
                    self.logger.warning(f"Rate limited. Waiting {wait_time} seconds before retry {attempt + 1}/{retries}")
                    time.sleep(wait_time)
                else:
                    self.logger.warning(f"Request failed with status {response.status_code}, attempt {attempt + 1}/{retries}")
                    time.sleep(self.retry_delay)
                    
            except requests.exceptions.ProxyError as e:
                self.logger.error(f"Proxy error on attempt {attempt + 1}: {e}")
                if attempt == retries - 1:
                    self.logger.warning("Attempting request without proxy...")
                    self.session.proxies = {}  # Remove proxy for final attempt
                time.sleep(self.retry_delay)
                
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request error on attempt {attempt + 1}: {e}")
                time.sleep(self.retry_delay)
                
        return None
        
    def collect_data(self):
        """Collect data using direct JSON endpoints with improved error handling"""
        subreddits = self.config.get('subreddits', ['wallstreetbets', 'stocks', 'investing'])
        timeframe = self.config.get('timeframe', 'week')
        post_limit = self.config.get('postLimit', 100)
        
        all_posts = []
        for subreddit in subreddits:
            # Use old.reddit.com for better compatibility
            url = f"https://old.reddit.com/r/{subreddit}/top.json?t={timeframe}&limit={post_limit}"
            self.logger.info(f"Fetching data from: {url}")
            
            response = self._make_request(url)
            if response:
                try:
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
                except Exception as e:
                    self.logger.error(f"Error processing data from r/{subreddit}: {str(e)}")
            
            # Respect rate limits between subreddits
            time.sleep(2)
                
        return pd.DataFrame(all_posts) if all_posts else pd.DataFrame()

    async def main(self):
        await self._initialize_session()
        # Proceed with data collection after session initialization
        df = await self.collect_data()