from praw import Reddit
import pandas as pd
import yaml
import os
from datetime import datetime, timedelta
import re

class RedditDataCollector:
    def __init__(self, config):
        """Initialize with either a config file path or config dictionary"""
        print("Initializing RedditDataCollector...")
        
        if isinstance(config, dict):
            self.config = config
            print("Using provided config dictionary")
        elif isinstance(config, (str, bytes, os.PathLike)):
            print(f"Loading config from file: {config}")
            with open(config, 'r') as file:
                self.config = yaml.safe_load(file)
        else:
            raise TypeError("config must be either a dictionary or a path to a config file")
        
        # Get credentials from environment
        self.client_id = os.environ.get('REDDIT_CLIENT_ID')
        self.client_secret = os.environ.get('REDDIT_CLIENT_SECRET')
        self.user_agent = os.environ.get('REDDIT_USER_AGENT')
        
        # Validate credentials
        if not all([self.client_id, self.client_secret, self.user_agent]):
            raise ValueError("Missing Reddit API credentials in environment variables")
        
        # Validate user agent format
        if not re.match(r'^script:[a-zA-Z0-9_-]+:v\d+\.\d+\s+\(by\s+/u/[a-zA-Z0-9_-]+\)$', self.user_agent):
            raise ValueError(
                f"Invalid user agent format: {self.user_agent}\n"
                "Must be: 'script:<app ID>:v<version> (by /u/<reddit username>)'\n"
                "Example: 'script:RedditSentimentAnalyzer:v1.0 (by /u/your_username)'"
            )
        
        print("\nReddit API Configuration:")
        print(f"✓ User Agent: {self.user_agent}")
        print(f"✓ Client ID: {'*' * len(self.client_id)}")
        print(f"✓ Client Secret: {'*' * 8}")
        
        # Initialize Reddit client
        try:
            self.reddit = Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent
            )
            # Verify credentials
            self.reddit.user.me()
            print("✓ Reddit API authentication successful")
        except Exception as e:
            raise ValueError(f"Reddit API authentication failed: {str(e)}")
        
        # Extract configuration
        self.subreddits = self.config.get('subreddits', [])
        self.time_filter = self.config.get('timeframe', 'week')
        self.post_limit = self.config.get('post_limit', 100)
        
        print(f"Configuration loaded:")
        print(f"- Subreddits: {self.subreddits}")
        print(f"- Time filter: {self.time_filter}")
        print(f"- Post limit: {self.post_limit}")

    def collect_data(self):
        """Collect data from specified subreddits"""
        print("\nStarting data collection process...")
        all_posts = []
        
        for subreddit_name in self.subreddits:
            try:
                print(f"\nProcessing r/{subreddit_name}:")
                print("- Initializing subreddit connection...")
                subreddit = self.reddit.subreddit(subreddit_name)
                
                # Test subreddit access
                print("- Testing subreddit access...")
                subreddit.display_name
                print("✓ Subreddit access verified")
                
                # Get posts
                print(f"- Fetching posts (limit: {self.post_limit}, timeframe: {self.time_filter})...")
                if self.time_filter == 'day':
                    posts = subreddit.top('day', limit=self.post_limit)
                elif self.time_filter == 'week':
                    posts = subreddit.top('week', limit=self.post_limit)
                elif self.time_filter == 'month':
                    posts = subreddit.top('month', limit=self.post_limit)
                else:
                    posts = subreddit.top('year', limit=self.post_limit)

                post_count = 0
                for post in posts:
                    post_data = {
                        'subreddit': subreddit_name,
                        'title': post.title,
                        'selftext': post.selftext,
                        'score': post.score,
                        'comments': post.num_comments,
                        'created_utc': datetime.fromtimestamp(post.created_utc),
                        'id': post.id,
                        'url': post.url
                    }
                    all_posts.append(post_data)
                    post_count += 1
                    
                    if post_count % 10 == 0:
                        print(f"  - Processed {post_count} posts...")
                
                print(f"✓ Successfully collected {post_count} posts from r/{subreddit_name}")
                
            except Exception as e:
                print(f"\n❌ Error collecting data from r/{subreddit_name}:")
                print(f"- Error type: {type(e).__name__}")
                print(f"- Error message: {str(e)}")
                if '401' in str(e):
                    print("- Authentication failed. Please check your credentials.")
                elif '403' in str(e):
                    print("- Access forbidden. Check if the subreddit is private or quarantined.")
                elif '404' in str(e):
                    print("- Subreddit not found. Check if the name is correct.")
                continue
        
        print("\nData collection summary:")
        print(f"- Total posts collected: {len(all_posts)}")
        print(f"- Subreddits processed: {len(self.subreddits)}")
        
        if not all_posts:
            print("⚠️ Warning: No posts were collected!")
            return pd.DataFrame(columns=[
                'subreddit', 'title', 'selftext', 'score', 'comments',
                'created_utc', 'id', 'url'
            ])
        
        df = pd.DataFrame(all_posts)
        print("\nDataFrame created successfully:")
        print(f"- Shape: {df.shape}")
        print(f"- Columns: {df.columns.tolist()}")
        return df

    def test_authentication(self):
        """Test Reddit API authentication"""
        try:
            print("\nTesting Reddit API authentication...")
            # Try to access user identity
            user = self.reddit.user.me()
            if user is None:
                print("⚠️ Warning: Authenticated but couldn't get user details")
                return True
            print(f"✓ Successfully authenticated as: {user.name}")
            return True
        except Exception as e:
            print("\n❌ Authentication test failed:")
            print(f"- Error type: {type(e).__name__}")
            print(f"- Error message: {str(e)}")
            if '401' in str(e):
                print("- Issue: Invalid credentials or incorrect format")
                print("- Solution: Verify your client_id and client_secret")
                print("- Note: Make sure you're using a 'script' type app")
            elif '403' in str(e):
                print("- Issue: Insufficient permissions")
                print("- Solution: Check app permissions and user agent format")
            return False