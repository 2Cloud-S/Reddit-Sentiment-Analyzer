import logging
import time
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from apify_client import ApifyClient
import os
import pandas as pd
import json
from src.oauth_handler import RedditOAuthHandler

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
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Initialize Apify client
        self._initialize_apify_client()
        
        self.reddit = None
        
    def _initialize_apify_client(self):
        """Initialize Apify client with residential proxies"""
        self.logger.info("\n=== Apify Client Initialization ===")
        try:
            self.apify_client = ApifyClient(os.environ['APIFY_TOKEN'])
            self.proxy_configuration = {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"],
                "countryCode": "US"
            }
            self.logger.info("✅ Apify client initialized with residential proxies")
            
            # Test proxy connection
            proxy_url = self.apify_client.proxy.get_proxy_url(**self.proxy_configuration)
            self.proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            self.logger.info("✅ Proxy configuration tested successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Apify client initialization failed: {e}")
            raise

    def _scrape_subreddit_posts(self, subreddit_name, timeframe, limit):
        """Scrape posts using Apify residential proxies"""
        self.logger.info(f"🔄 Scraping r/{subreddit_name} with timeframe: {timeframe}")
        
        posts = []
        try:
            # Construct URL based on timeframe
            url = f"https://old.reddit.com/r/{subreddit_name}/top/?t={timeframe}"
            
            response = requests.get(url, proxies=self.proxies, headers=self.headers, timeout=30)
            self.logger.debug(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'lxml')
                
                # Find all post elements
                post_elements = soup.find_all('div', class_='thing')
                self.logger.info(f"Found {len(post_elements)} posts")
                
                for element in post_elements[:limit]:
                    try:
                        # Extract post data
                        post = {
                            'id': element.get('id', '').split('_')[-1],
                            'title': element.find('a', class_='title').text.strip() if element.find('a', class_='title') else '',
                            'selftext': element.find('div', class_='usertext-body').text.strip() if element.find('div', class_='usertext-body') else '',
                            'score': int(element.find('div', class_='score').get('title', 0)) if element.find('div', class_='score') else 0,
                            'created_utc': datetime.fromtimestamp(int(element.get('data-timestamp', 0)) / 1000) if element.get('data-timestamp') else datetime.now(),
                            'num_comments': int(element.find('a', class_='comments').text.split()[0].replace(',', '')) if element.find('a', class_='comments') else 0,
                            'subreddit': subreddit_name,
                            'url': f"https://reddit.com{element.find('a', class_='title')['href']}" if element.find('a', class_='title') else ''
                        }
                        
                        # Add post to list
                        posts.append(post)
                        self.logger.debug(f"Processed post: {post['id']}")
                        
                        # Respect rate limits
                        time.sleep(0.5)
                        
                    except Exception as e:
                        self.logger.warning(f"⚠️ Error processing post: {e}")
                        continue
                        
            else:
                self.logger.error(f"❌ Failed to fetch subreddit: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"❌ Web scraping failed: {e}")
            
        return posts

    def authenticate(self):
        """Set up OAuth authentication"""
        auth_handler = RedditOAuthHandler(
            client_id=self.config['clientId'],
            client_secret=self.config['clientSecret'],
            username=self.config['username'],
            password=self.config['password'],
            user_agent=self.config.get('userAgent', 'SentimentAnalyzer/1.0')
        )
        self.reddit = auth_handler.authenticate()
        
    def collect_data(self):
        """Collect data from Reddit using authenticated client"""
        if not self.reddit:
            self.authenticate()
            
        data = []
        for subreddit_name in self.config['subreddits']:
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                
                # Get posts based on timeframe
                if self.config['timeframe'] == 'all':
                    posts = subreddit.top(limit=self.config['postLimit'])
                else:
                    posts = subreddit.top(time_filter=self.config['timeframe'], 
                                        limit=self.config['postLimit'])
                
                for post in posts:
                    post_data = {
                        'id': post.id,
                        'subreddit': subreddit_name,
                        'title': post.title,
                        'selftext': post.selftext,
                        'score': post.score,
                        'comments': post.num_comments,
                        'created_utc': datetime.fromtimestamp(post.created_utc),
                        'url': post.url,
                        'author': str(post.author),
                        'upvote_ratio': post.upvote_ratio
                    }
                    data.append(post_data)
                    
            except Exception as e:
                print(f"Error collecting data from r/{subreddit_name}: {str(e)}")
                continue
                
        return pd.DataFrame(data)