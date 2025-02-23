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
        
        # Initialize Apify client (without proxy)
        self.apify_client = ApifyClient(os.environ['APIFY_TOKEN'])
        self.logger.info("✅ Apify client initialized")
        
        self.reddit = None
        
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
                self.logger.info(f"Collecting data from r/{subreddit_name}")
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
                    
                # Add delay between subreddits to respect rate limits
                time.sleep(2)
                    
            except Exception as e:
                self.logger.error(f"Error collecting data from r/{subreddit_name}: {str(e)}")
                continue
                
        return pd.DataFrame(data)