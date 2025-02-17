from praw import Reddit
from prawcore.exceptions import (
    ResponseException,
    RequestException,
    OAuthException
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
import base64

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
        self.rate_limit_remaining = 60
        self.rate_limit_reset = 0
        
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
                # Initialize with script app credentials
                self.reddit = Reddit(
                    client_id=self.config['client_id'],
                    client_secret=self.config['client_secret'],
                    user_agent=self.config['user_agent'],
                    username=self.config.get('redditUsername'),
                    password=self.config.get('redditPassword'),
                    check_for_updates=False,
                    requestor_kwargs={
                        'timeout': 30,
                        'headers': {
                            'User-Agent': self.config['user_agent']
                        }
                    }
                )
                
                # Get OAuth token directly if needed
                if not self._validate_authentication():
                    auth = base64.b64encode(
                        f"{self.config['client_id']}:{self.config['client_secret']}".encode()
                    ).decode()
                    
                    headers = {
                        'User-Agent': self.config['user_agent'],
                        'Authorization': f'Basic {auth}'
                    }
                    
                    data = {
                        'grant_type': 'client_credentials',
                        'duration': 'temporary'
                    }
                    
                    self.logger.info("🔑 Obtaining OAuth token...")
                    response = requests.post(
                        'https://www.reddit.com/api/v1/access_token',
                        headers=headers,
                        data=data
                    )
                    
                    if response.status_code == 200:
                        token_data = response.json()
                        self.logger.info("✅ OAuth token obtained successfully")
                        self.reddit._core._authorizer.access_token = token_data['access_token']
                    else:
                        self.logger.error(f"❌ Failed to obtain OAuth token: {response.text}")
                        raise ResponseException(response)
                
                self.logger.info("✅ Reddit client initialized successfully")
                break
                
            except OAuthException as e:
                self.logger.error(f"Authentication error (attempt {attempt + 1}/{self.max_retries}): {e}")
                self.logger.error("🔑 Verify your credentials and user agent format")
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(self.retry_delay * (attempt + 1))
                
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

    def _check_rate_limit(self, response):
        """Check rate limit from response headers"""
        try:
            headers = response.headers if hasattr(response, 'headers') else {}
            
            # Update rate limit info
            self.rate_limit_remaining = int(headers.get('x-ratelimit-remaining', 60))
            self.rate_limit_reset = int(headers.get('x-ratelimit-reset', 0))
            self.rate_limit_used = int(headers.get('x-ratelimit-used', 0))
            
            self.logger.debug(f"Rate Limits - Remaining: {self.rate_limit_remaining}, Reset: {self.rate_limit_reset}s, Used: {self.rate_limit_used}")
            
            if self.rate_limit_remaining <= 0:
                wait_time = self.rate_limit_reset + 1
                self.logger.warning(f"⚠️ Rate limit exceeded. Waiting {wait_time} seconds.")
                time.sleep(wait_time)
                return True
            elif self.rate_limit_remaining < 10:
                wait_time = 2
                self.logger.info(f"⚠️ Rate limit approaching. Adding delay of {wait_time}s")
                time.sleep(wait_time)
            
            return False
            
        except Exception as e:
            self.logger.warning(f"⚠️ Error checking rate limit: {e}")
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
                    
                except ResponseException as e:
                    if hasattr(e, 'response') and e.response.status_code == 429:  # Too Many Requests
                        self.logger.warning(f"⚠️ Rate limit hit for r/{subreddit_name}")
                        self._check_rate_limit(e.response)
                    else:
                        self.logger.error(f"❌ API error for r/{subreddit_name}: {e}")
                        time.sleep(5)
                    continue
                    
                except RedditAPIException as e:
                    self.logger.warning(f"⚠️ Reddit API error for r/{subreddit_name}: {e}")
                    time.sleep(5)
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
                # Check rate limit before each request
                if hasattr(submission, '_reddit'):
                    response = submission._reddit._core._requestor._http.history[-1] if submission._reddit._core._requestor._http.history else None
                    if response:
                        self._check_rate_limit(response)
                
                posts.append(self._process_submission(submission))
                time.sleep(0.5)  # Minimum delay between requests
                
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