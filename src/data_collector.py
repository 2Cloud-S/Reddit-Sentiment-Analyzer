import logging
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from apify_client import ApifyClient
import os
import pandas as pd
import json

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
        
    def _initialize_apify_client(self):
        """Initialize Apify client with residential proxies"""
        self.logger.info("\n=== Apify Client Initialization ===")
        try:
            self.apify_client = ApifyClient(os.environ['APIFY_TOKEN'])
            
            # Create a new proxy configuration
            self.proxy_configuration = {
                "useApifyProxy": True,
                "groups": ["RESIDENTIAL"],
                "countryCode": "US"
            }
            
            # Initialize session with proxy rotation
            self.session = requests.Session()
            self.session.headers.update(self.headers)
            
            # Log success
            self.logger.info("✅ Apify client initialized with residential proxies")
            
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

    def collect_data(self):
        """Collect data using direct JSON endpoints instead of API"""
        subreddits = self.config.get('subreddits', ['wallstreetbets', 'stocks', 'investing'])
        timeframe = self.config.get('timeframe', 'week')
        post_limit = self.config.get('postLimit', 100)
        
        all_posts = []
        for subreddit in subreddits:
            try:
                # Use the JSON endpoint
                url = f"https://www.reddit.com/r/{subreddit}/top.json?t={timeframe}&limit={post_limit}"
                response = self.session.get(url)
                
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
                    
                    # Rate limiting to avoid getting blocked
                    time.sleep(2)
                else:
                    self.logger.error(f"Error accessing r/{subreddit}: Status code {response.status_code}")
                    
            except Exception as e:
                self.logger.error(f"Error collecting data from r/{subreddit}: {str(e)}")
                continue
                
        return pd.DataFrame(all_posts) if all_posts else pd.DataFrame()