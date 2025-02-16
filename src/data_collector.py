from praw import Reddit
import pandas as pd
import yaml
import os
from datetime import datetime, timedelta
import re
import time
from prawcore import Requestor
from prawcore.auth import ScriptAuthorizer, TrustedAuthenticator
import base64
import sys
import platform
import praw
import logging
import requests
from prawcore.exceptions import ResponseException, RequestException, RateLimitExceeded, OAuthException

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
        self.max_retries = 3
        self.retry_delay = 5
        
        # Initialize Reddit instance with retry logic
        self._initialize_reddit_client()
        
    def _initialize_reddit_client(self):
        """Initialize Reddit client with retry logic and validation"""
        self.logger.info("\n=== Reddit Client Initialization ===")
        
        # Log environment and network info
        self._log_environment_info()
        
        for attempt in range(self.max_retries):
            try:
                self.reddit = Reddit(
                    client_id=self.config['client_id'],
                    client_secret=self.config['client_secret'],
                    user_agent=self.config['user_agent'],
                    username=self.config.get('redditUsername'),
                    password=self.config.get('redditPassword'),
                    check_for_updates=False
                )
                
                # Validate authentication
                self._validate_authentication()
                self.logger.info("✅ Reddit client initialized successfully")
                break
                
            except OAuthException as e:
                self.logger.error(f"Authentication error (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(self.retry_delay)
                
            except Exception as e:
                self.logger.error(f"Initialization error (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(self.retry_delay)

    def _log_environment_info(self):
        """Log environment and network information"""
        try:
            # Test network connectivity
            ip_response = requests.get('https://api.ipify.org?format=json', timeout=5)
            self.logger.info(f"🌐 Container IP: {ip_response.json()['ip']}")
            
            # Test Reddit API accessibility
            reddit_response = requests.get('https://www.reddit.com/api/v1/access_token',
                                         headers={'User-Agent': self.config['user_agent']},
                                         timeout=5)
            self.logger.info(f"📡 Reddit API Status: {reddit_response.status_code}")
            self.logger.info(f"🔑 Reddit API Headers: {dict(reddit_response.headers)}")
            
        except Exception as e:
            self.logger.warning(f"⚠️ Network diagnostics failed: {e}")

    def _validate_authentication(self):
        """Validate Reddit API authentication"""
        try:
            # Test with read-only operation
            test_subreddit = self.reddit.subreddit('announcements')
            next(test_subreddit.hot(limit=1))
            self.logger.info("✅ Authentication validated successfully")
            
        except Exception as e:
            self.logger.error("❌ Authentication validation failed")
            if hasattr(e, 'response'):
                self.logger.error(f"Response Status: {e.response.status_code}")
                self.logger.error(f"Response Headers: {dict(e.response.headers)}")
            raise

    def collect_data(self):
        """Collect data with enhanced error handling and rate limiting"""
        try:
            all_posts = []
            for subreddit_name in self.config['subreddits']:
                self.logger.info(f"\n📥 Collecting data from r/{subreddit_name}")
                
                try:
                    subreddit = self.reddit.subreddit(subreddit_name)
                    posts = self._collect_subreddit_posts(subreddit)
                    all_posts.extend(posts)
                    
                except RateLimitExceeded as e:
                    self.logger.warning(f"⚠️ Rate limit exceeded for r/{subreddit_name}: {e}")
                    time.sleep(int(e.response.headers.get('x-ratelimit-reset', 60)))
                    continue
                    
                except Exception as e:
                    self.logger.error(f"❌ Error collecting from r/{subreddit_name}: {e}")
                    continue
            
            return pd.DataFrame(all_posts)
            
        except Exception as e:
            self.logger.error(f"❌ Data collection failed: {e}")
            return pd.DataFrame()

    def _collect_subreddit_posts(self, subreddit):
        """Collect posts from a subreddit with rate limiting"""
        posts = []
        timeframe = self.config['timeframe']
        limit = self.config['postLimit']
        
        try:
            if timeframe == 'all':
                submissions = subreddit.top(limit=limit)
            else:
                submissions = subreddit.top(time_filter=timeframe, limit=limit)
            
            for submission in submissions:
                posts.append(self._process_submission(submission))
                time.sleep(0.5)  # Rate limiting
                
        except Exception as e:
            self.logger.error(f"Error in subreddit collection: {e}")
            
        return posts

    def test_authentication(self):
        """Test Reddit API authentication"""
        try:
            self.logger.info("\nTesting Reddit API authentication...")
            # Try to access user identity
            user = self.reddit.user.me()
            if user is None:
                self.logger.warning("⚠️ Warning: Authenticated but couldn't get user details")
                return True
            self.logger.info(f"✓ Successfully authenticated as: {user.name}")
            return True
        except Exception as e:
            self.logger.error("\n❌ Authentication test failed:")
            self.logger.error(f"- Error type: {type(e).__name__}")
            self.logger.error(f"- Error message: {str(e)}")
            if '401' in str(e):
                self.logger.error("- Issue: Invalid credentials or incorrect format")
                self.logger.error("- Solution: Verify your client_id and client_secret")
                self.logger.error("- Note: Make sure you're using a 'script' type app")
            elif '403' in str(e):
                self.logger.error("- Issue: Insufficient permissions")
                self.logger.error("- Solution: Check app permissions and user agent format")
            return False