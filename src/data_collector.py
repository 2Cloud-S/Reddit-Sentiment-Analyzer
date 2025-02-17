from praw import Reddit
from prawcore.exceptions import (
    ResponseException,
    RequestException,
    OAuthException,
    RateLimitExceeded
)
from praw.exceptions import RedditAPIException
import pandas as pd
import yaml
import os
from datetime import datetime, timedelta
import re
import time
import logging
import requests

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
        
        # Construct proper user agent
        if 'user_agent' not in self.config:
            app_version = self.config.get('appVersion', 'v1.0').lstrip('v')
            app_name = self.config.get('appName', 'RedditSentimentAnalyzer')
            username = self.config.get('redditUsername', 'anonymous')
            self.config['user_agent'] = f"script:{app_name}:{app_version} (by /u/{username})"
        
        self.logger.info(f"🔧 Using User-Agent: {self.config['user_agent']}")
        
        # Log environment and network info
        self._log_environment_info()
        
        for attempt in range(self.max_retries):
            try:
                # Initialize with required parameters
                self.reddit = Reddit(
                    client_id=self.config['client_id'],
                    client_secret=self.config['client_secret'],
                    user_agent=self.config['user_agent'],
                    username=self.config.get('redditUsername'),
                    password=self.config.get('redditPassword'),
                    check_for_updates=False,
                    requestor_kwargs={'timeout': 30}
                )
                
                # Validate authentication
                self._validate_authentication()
                self.logger.info("✅ Reddit client initialized successfully")
                break
                
            except OAuthException as e:
                self.logger.error(f"Authentication error (attempt {attempt + 1}/{self.max_retries}): {e}")
                self.logger.error("🔑 Verify your credentials and user agent format")
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                
            except Exception as e:
                self.logger.error(f"Initialization error (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(self.retry_delay * (attempt + 1))

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
            # First test with user identity
            user = self.reddit.user.me()
            if user:
                self.logger.info(f"✓ Successfully authenticated as: {user.name}")
            
            # Test with read-only operation
            test_subreddit = self.reddit.subreddit('announcements')
            next(test_subreddit.hot(limit=1))
            self.logger.info("✅ API access validated successfully")
            
        except OAuthException as e:
            self.logger.error("❌ Authentication validation failed")
            self.logger.error("- Ensure your Reddit app is type 'script'")
            self.logger.error("- Verify client_id and client_secret are correct")
            self.logger.error("- Check if username and password are required")
            raise
            
        except Exception as e:
            self.logger.error("❌ API access validation failed")
            if hasattr(e, 'response'):
                self.logger.error(f"Response Status: {e.response.status_code}")
                self.logger.error(f"Response Headers: {dict(e.response.headers)}")
            raise

    def _handle_rate_limit(self, response_headers):
        """Handle rate limiting based on response headers"""
        try:
            if 'x-ratelimit-remaining' in response_headers:
                remaining = float(response_headers['x-ratelimit-remaining'])
                reset_time = int(response_headers['x-ratelimit-reset'])
                used = response_headers.get('x-ratelimit-used', '0')
                
                self.logger.debug(f"Rate Limit Status: {used} used, {remaining} remaining, reset in {reset_time}s")
                
                if remaining <= 0:
                    sleep_time = reset_time + 1
                    self.logger.warning(f"⚠️ Rate limit reached. Sleeping for {sleep_time} seconds")
                    time.sleep(sleep_time)
                    return True
                elif remaining < 10:  # Proactive rate limit handling
                    sleep_time = 2
                    self.logger.info(f"⚠️ Rate limit approaching. Adding delay of {sleep_time}s")
                    time.sleep(sleep_time)
            return False
        except Exception as e:
            self.logger.error(f"Error handling rate limit: {e}")
            time.sleep(5)  # Default safety delay
            return False

    def collect_data(self):
        """Collect data with enhanced error handling"""
        try:
            all_posts = []
            for subreddit_name in self.config['subreddits']:
                self.logger.info(f"\n📥 Collecting data from r/{subreddit_name}")
                
                try:
                    subreddit = self.reddit.subreddit(subreddit_name)
                    posts = self._collect_subreddit_posts(subreddit)
                    all_posts.extend(posts)
                    
                except RateLimitExceeded as e:
                    self.logger.warning(f"⚠️ Rate limit hit for r/{subreddit_name}")
                    # Get rate limit info from response headers if available
                    if hasattr(e, 'response') and 'x-ratelimit-reset' in e.response.headers:
                        reset_time = int(e.response.headers['x-ratelimit-reset'])
                        self.logger.info(f"Waiting for {reset_time} seconds")
                        time.sleep(reset_time + 1)
                    else:
                        self.logger.info("Rate limit info not available, waiting 60 seconds")
                        time.sleep(60)
                    continue
                    
                except RedditAPIException as e:
                    self.logger.warning(f"⚠️ Reddit API error for r/{subreddit_name}: {e}")
                    time.sleep(5)  # Short delay before retrying
                    continue
                    
                except Exception as e:
                    self.logger.error(f"❌ Error collecting from r/{subreddit_name}: {e}")
                    continue
            
            return pd.DataFrame(all_posts)
            
        except Exception as e:
            self.logger.error(f"❌ Data collection failed: {e}")
            self.logger.exception("Full traceback:")
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

    def _process_submission(self, submission):
        """Process a submission and extract relevant data"""
        return {
            'id': submission.id,
            'title': submission.title,
            'selftext': submission.selftext,
            'score': submission.score,
            'created_utc': datetime.fromtimestamp(submission.created_utc),
            'num_comments': submission.num_comments,
            'subreddit': submission.subreddit.display_name
        }

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