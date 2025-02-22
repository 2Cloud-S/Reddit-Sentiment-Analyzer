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
from urllib.parse import parse_qs, urlparse

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
        
        # Default headers that mimic a real browser
        self.default_headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json,text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
        
        # Merge custom headers if provided
        if 'customHeaders' in config and config['customHeaders']:
            self.default_headers.update(config['customHeaders'])
            
        # Setup cookies if provided
        self.cookies = {}
        if 'sessionCookies' in config and config['sessionCookies']:
            self.cookies = self._parse_cookie_string(config['sessionCookies'])
        
        # Initialize session variable
        self.session = None
        
    def _parse_cookie_string(self, cookie_string):
        """Parse cookie string into a dictionary"""
        cookies = {}
        if not cookie_string:
            return cookies
            
        try:
            cookie_pairs = cookie_string.split(';')
            for pair in cookie_pairs:
                if '=' in pair:
                    key, value = pair.strip().split('=', 1)
                    cookies[key] = value
        except Exception as e:
            self.logger.error(f"Error parsing cookies: {str(e)}")
            
        return cookies

    async def _initialize_session(self):
        """Initialize session with cookies and headers"""
        self.logger.info("\n=== Session Initialization ===")
        
        # Initialize session with cookie jar
        cookie_jar = aiohttp.CookieJar(unsafe=True)
        self.session = aiohttp.ClientSession(
            cookie_jar=cookie_jar,
            headers=self.default_headers
        )
        
        # Add cookies to session if available
        if self.cookies:
            for key, value in self.cookies.items():
                self.session.cookie_jar.update_cookies({key: value})
                
        self.logger.info("✅ Session initialized with cookies and headers")
        
        # Test the session
        await self._test_session()

    async def _test_session(self):
        """Test the session configuration"""
        try:
            async with self.session.get('https://old.reddit.com/api/v1/me.json') as response:
                self.logger.info(f"Session test status: {response.status}")
                if response.status == 200:
                    self.logger.info("✅ Session authentication successful")
                else:
                    self.logger.warning("⚠️ Session authentication may not be optimal")
        except Exception as e:
            self.logger.error(f"Session test failed: {str(e)}")

    async def _make_request(self, url, retries=3, delay=2):
        """Make a request with automatic retry and error handling"""
        for attempt in range(retries):
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 403:
                        self.logger.warning(f"Access forbidden (403) - Attempt {attempt + 1}/{retries}")
                        if attempt < retries - 1:
                            await asyncio.sleep(delay * (attempt + 1))  # Exponential backoff
                    else:
                        self.logger.warning(f"Request failed with status {response.status} - Attempt {attempt + 1}/{retries}")
                        if attempt < retries - 1:
                            await asyncio.sleep(delay)
            except Exception as e:
                self.logger.error(f"Request error on attempt {attempt + 1}: {str(e)}")
                if attempt < retries - 1:
                    await asyncio.sleep(delay)
        return None

    async def collect_data(self):
        """Collect data from Reddit with improved error handling"""
        if not self.session:
            await self._initialize_session()
            
        subreddits = self.config.get('subreddits', ['stocks'])
        timeframe = self.config.get('timeframe', 'day')
        post_limit = self.config.get('postLimit', 10)
        
        all_posts = []
        for subreddit in subreddits:
            url = f"https://old.reddit.com/r/{subreddit}/top.json?t={timeframe}&limit={post_limit}"
            self.logger.info(f"Fetching data from: {url}")
            
            response = await self._make_request(url)
            if response and 'data' in response and 'children' in response['data']:
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
                        'author': post_data.get('author', '[deleted]'),
                        'id': post_data.get('id', ''),
                        'permalink': post_data.get('permalink', '')
                    })
                
                self.logger.info(f"Successfully collected {len(posts)} posts from r/{subreddit}")
            else:
                self.logger.error(f"Failed to collect data from r/{subreddit}")
            
            # Respect rate limits
            await asyncio.sleep(2)
        
        return pd.DataFrame(all_posts) if all_posts else pd.DataFrame()

    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
            self.logger.info("Session closed")

    async def main(self):
        await self._initialize_session()
        # Proceed with data collection after session initialization
        df = await self.collect_data()
        await self.session.close()  # Close the session when done