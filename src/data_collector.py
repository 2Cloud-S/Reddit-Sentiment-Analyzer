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
        
        # OAuth credentials
        self.client_id = config['client_id']
        self.client_secret = config['client_secret']
        self.user_agent = config['user_agent']
        
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
        """Initialize session with OAuth authentication"""
        self.logger.info("\n=== Session Initialization ===")
        
        # Create a session with headers
        self.session = aiohttp.ClientSession(
            headers={
                'User-Agent': self.user_agent
            }
        )
        
        # Authenticate and get access token
        await self._authenticate()
        
    async def _authenticate(self):
        """Authenticate with Reddit API using OAuth"""
        auth = aiohttp.BasicAuth(self.client_id, self.client_secret)
        data = {
            'grant_type': 'client_credentials'
        }
        
        async with self.session.post('https://www.reddit.com/api/v1/access_token', auth=auth, data=data) as response:
            if response.status == 200:
                token_info = await response.json()
                self.access_token = token_info['access_token']
                self.logger.info("✅ Authentication successful")
            else:
                self.logger.error(f"❌ Authentication failed: {response.status} {await response.text()}")
                raise Exception("Authentication failed")
        
    async def _make_request(self, url):
        """Make a request to the Reddit API"""
        headers = {
            'Authorization': f'bearer {self.access_token}',
            'User-Agent': self.user_agent
        }
        
        async with self.session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                self.logger.error(f"Request failed with status {response.status}: {await response.text()}")
                return None

    async def collect_data(self):
        """Collect data from Reddit using the API"""
        await self._initialize_session()
        
        subreddits = self.config.get('subreddits', ['stocks'])
        timeframe = self.config.get('timeframe', 'day')
        post_limit = self.config.get('postLimit', 10)
        
        all_posts = []
        for subreddit in subreddits:
            url = f"https://oauth.reddit.com/r/{subreddit}/top.json?t={timeframe}&limit={post_limit}"
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