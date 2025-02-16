from praw import Reddit
import pandas as pd
import yaml
import os
from datetime import datetime, timedelta
import re
import time

class RedditDataCollector:
    def __init__(self, config):
        """Initialize with configuration dictionary"""
        print("Initializing RedditDataCollector...")
        
        # Validate required fields
        required_fields = ['client_id', 'client_secret', 'user_agent']
        missing_fields = [field for field in required_fields if not config.get(field)]
        if missing_fields:
            raise ValueError(f"Missing required fields in config: {missing_fields}")
        
        # Format user agent if needed
        user_agent = config['user_agent']
        user_agent_pattern = r'^script:[a-zA-Z0-9_-]+:v\d+\.\d+\s+\(by\s+/u/[a-zA-Z0-9_-]+\)$'
        if not re.match(user_agent_pattern, user_agent):
            print(f"⚠️ Invalid user agent format: {user_agent}")
            print("Attempting to fix user agent format...")
            try:
                app_name = config.get('appName', 'RedditSentimentAnalyzer')
                version = config.get('appVersion', 'v1.0').lstrip('v')
                username = config.get('redditUsername', 'anonymous')
                user_agent = f"script:{app_name}:v{version} (by /u/{username})"
                config['user_agent'] = user_agent
                print(f"✓ Fixed user agent: {user_agent}")
            except Exception as e:
                raise ValueError(f"Could not format user agent: {str(e)}")

        # Initialize Reddit client with read-only mode and proper authentication
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.reddit = Reddit(
                    client_id=config['client_id'],
                    client_secret=config['client_secret'],
                    user_agent=config['user_agent'],
                    username=config.get('redditUsername'),
                    password=None,  # We're using script auth without password
                    read_only=True  # Explicitly set read-only mode
                )
                
                # Test authentication with a simple API call
                self.reddit.auth.scopes()
                print("✓ Reddit API authentication successful")
                
                # Store configuration
                self.config = config
                self.subreddits = config.get('subreddits', [])
                self.time_filter = config.get('timeframe', 'week')
                self.post_limit = config.get('postLimit', 100)
                break
                
            except Exception as e:
                print(f"\n⚠️ Authentication attempt {attempt + 1} failed:")
                print(f"- Error: {str(e)}")
                if attempt == max_retries - 1:
                    raise ValueError(f"Failed to initialize Reddit client after {max_retries} attempts")
                time.sleep(2)  # Add delay between retries

    def collect_data(self):
        """Collect data from specified subreddits"""
        all_posts = []
        
        for subreddit_name in self.subreddits:
            try:
                print(f"\nProcessing r/{subreddit_name}:")
                print("- Initializing subreddit connection...")
                
                # Use proper error handling for subreddit access
                try:
                    subreddit = self.reddit.subreddit(subreddit_name)
                    # Test access with a simple attribute
                    display_name = subreddit.display_name
                    print(f"✓ Connected to r/{display_name}")
                except Exception as e:
                    print(f"❌ Failed to access r/{subreddit_name}: {str(e)}")
                    continue

                print(f"- Fetching posts (limit: {self.post_limit}, timeframe: {self.time_filter})...")
                
                # Collect posts with proper error handling
                posts = []
                try:
                    for post in subreddit.top(time_filter=self.time_filter, limit=self.post_limit):
                        try:
                            posts.append({
                                'subreddit': subreddit_name,
                                'title': post.title,
                                'text': post.selftext,
                                'score': post.score,
                                'comments': post.num_comments,
                                'created_utc': post.created_utc,
                                'id': post.id,
                                'url': post.url
                            })
                        except Exception as post_e:
                            print(f"- Error processing post: {str(post_e)}")
                            continue
                except Exception as fetch_e:
                    print(f"❌ Error fetching posts: {str(fetch_e)}")
                    continue

                print(f"✓ Collected {len(posts)} posts from r/{subreddit_name}")
                all_posts.extend(posts)
                
            except Exception as e:
                print(f"\n❌ Error collecting data from r/{subreddit_name}:")
                print(f"- Error type: {type(e).__name__}")
                print(f"- Error message: {str(e)}")
                continue
        
        print(f"\nData collection summary:")
        print(f"- Total posts collected: {len(all_posts)}")
        print(f"- Subreddits processed: {len(self.subreddits)}")
        
        if not all_posts:
            print("⚠️ Warning: No posts were collected!")
            return pd.DataFrame()
        
        return pd.DataFrame(all_posts)

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