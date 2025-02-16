from praw import Reddit
import pandas as pd
import yaml
import os
from datetime import datetime, timedelta

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
        
        # Extract configuration
        self.subreddits = self.config.get('subreddits', [])
        self.time_filter = self.config.get('timeframe', 'week')
        self.post_limit = self.config.get('post_limit', 100)
        
        print(f"Configuration loaded:")
        print(f"- Subreddits: {self.subreddits}")
        print(f"- Time filter: {self.time_filter}")
        print(f"- Post limit: {self.post_limit}")
        
        # Format user agent properly
        user_agent = os.environ.get('REDDIT_USER_AGENT')
        if not user_agent or user_agent == 'SentimentAnalysis/1.0':
            # Create a more Reddit-compliant user agent
            user_agent = f"script:reddit-sentiment-analyzer:v1.0 (by /u/your_reddit_username)"
            os.environ['REDDIT_USER_AGENT'] = user_agent
        
        print(f"Using user agent: {user_agent}")
        
        # Initialize Reddit client with read-only mode
        try:
            self.reddit = Reddit(
                client_id=os.environ.get('REDDIT_CLIENT_ID'),
                client_secret=os.environ.get('REDDIT_CLIENT_SECRET'),
                user_agent=user_agent,
                read_only=True
            )
            print("Reddit client initialized in read-only mode")
            
            # Verify credentials
            print("\nVerifying Reddit API credentials...")
            test_subreddit = self.reddit.subreddit('test')
            test_subreddit.display_name
            print("✓ Credentials verified successfully")
            
            # Add authentication test
            if not self.test_authentication():
                raise ValueError("Reddit API authentication failed")
            
        except Exception as e:
            print("\n❌ Reddit API Authentication Error:")
            if '401' in str(e):
                print("- Status: 401 Unauthorized")
                print("- Cause: Invalid credentials")
                print("- Solution: Double-check your Client ID and Client Secret")
            elif '403' in str(e):
                print("- Status: 403 Forbidden")
                print("- Cause: Insufficient permissions")
                print("- Solution: Ensure your Reddit API application has the correct scope")
            else:
                print(f"- Unexpected error: {str(e)}")
            raise

    def collect_data(self):
        """Collect data from specified subreddits"""
        print("\nStarting data collection process...")
        all_posts = []
        
        for subreddit_name in self.subreddits:
            try:
                print(f"\nProcessing r/{subreddit_name}:")
                subreddit = self.reddit.subreddit(subreddit_name)
                
                # Verify subreddit access first
                print("- Testing subreddit access...")
                display_name = subreddit.display_name
                print(f"✓ Subreddit verified: r/{display_name}")
                
                # Get posts with detailed error handling
                print(f"- Fetching {self.post_limit} posts from past {self.time_filter}...")
                posts = subreddit.top(time_filter=self.time_filter, limit=self.post_limit)
                
                post_count = 0
                for post in posts:
                    try:
                        post_data = {
                            'subreddit': subreddit_name,
                            'title': post.title,
                            'selftext': post.selftext,
                            'score': post.score,
                            'comments': post.num_comments,
                            'created_utc': post.created_utc,
                            'id': post.id,
                            'url': post.url
                        }
                        all_posts.append(post_data)
                        post_count += 1
                        
                        if post_count % 10 == 0:
                            print(f"  - Processed {post_count} posts...")
                            
                    except Exception as e:
                        print(f"  ⚠️ Error processing post: {str(e)}")
                        continue
                
                print(f"✓ Successfully collected {post_count} posts from r/{subreddit_name}")
                
            except Exception as e:
                print(f"\n❌ Error collecting data from r/{subreddit_name}:")
                print(f"- Error type: {type(e).__name__}")
                print(f"- Error message: {str(e)}")
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
            # Test with a public subreddit first
            test_subreddit = self.reddit.subreddit('announcements')
            # Try to get the subreddit's display name (lightweight test)
            display_name = test_subreddit.display_name
            print(f"✓ Successfully accessed test subreddit: r/{display_name}")
            
            # Try to get a single post to verify data access
            for post in test_subreddit.hot(limit=1):
                print("✓ Successfully retrieved test post")
                break
            
            return True
        
        except Exception as e:
            print("\n❌ Authentication test failed:")
            print(f"- Error type: {type(e).__name__}")
            print(f"- Error message: {str(e)}")
            if '401' in str(e):
                print("- Issue: Invalid credentials or incorrect format")
                print("- Solution: Verify your client_id and client_secret")
                print("- Note: Make sure you're using a 'script' type app")
                print("- User Agent: ", os.environ.get('REDDIT_USER_AGENT'))
            elif '403' in str(e):
                print("- Issue: Insufficient permissions")
                print("- Solution: Check app permissions and user agent format")
            return False