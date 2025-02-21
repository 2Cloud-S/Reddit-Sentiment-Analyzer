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
import asyncio
import aiohttp

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
        self.session = aiohttp.ClientSession()
        self.logger.info("✅ Session initialized")
        
    async def _make_request(self, url):
        """Make a request with automatic retry and user agent rotation"""
        for attempt in range(3):
            try:
                headers = {'User-Agent': random.choice(self.user_agents)}
                async with self.session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        self.logger.warning(f"Request failed with status {response.status}, attempt {attempt + 1}/3")
            except Exception as e:
                self.logger.error(f"Request error on attempt {attempt + 1}: {e}")
        return None
        
    async def collect_data(self):
        """Collect data using direct JSON endpoints with improved error handling"""
        subreddits = self.config.get('subreddits', ['wallstreetbets', 'stocks', 'investing'])
        timeframe = self.config.get('timeframe', 'week')
        post_limit = self.config.get('postLimit', 100)
        
        all_posts = []
        for subreddit in subreddits:
            # Use old.reddit.com for better compatibility
            url = f"https://old.reddit.com/r/{subreddit}/top.json?t={timeframe}&limit={post_limit}"
            self.logger.info(f"Fetching data from: {url}")
            
            response = await self._make_request(url)
            if response:
                try:
                    posts = response['data']['children']
                    
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
            await asyncio.sleep(2)  # Use asyncio.sleep for async delay
                
        return pd.DataFrame(all_posts) if all_posts else pd.DataFrame()

    async def main(self):
        await self._initialize_session()
        # Proceed with data collection after session initialization
        df = await self.collect_data()
        await self.session.close()  # Close the session when done