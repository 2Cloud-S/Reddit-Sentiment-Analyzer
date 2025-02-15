from praw import Reddit
import pandas as pd
import yaml
import os
from datetime import datetime, timedelta

class RedditDataCollector:
    def __init__(self, config):
        """Initialize with either a config file path or config dictionary"""
        if isinstance(config, dict):
            self.config = config
        elif isinstance(config, (str, bytes, os.PathLike)):
            with open(config, 'r') as file:
                self.config = yaml.safe_load(file)
        else:
            raise TypeError("config must be either a dictionary or a path to a config file")
        
        # Initialize Reddit client
        try:
            self.reddit = Reddit(
                client_id=os.environ['REDDIT_CLIENT_ID'],
                client_secret=os.environ['REDDIT_CLIENT_SECRET'],
                user_agent=os.environ['REDDIT_USER_AGENT']
            )
            print("Debug - Reddit client initialized successfully")
        except Exception as e:
            print(f"Error initializing Reddit client: {str(e)}")
            raise
        
        # Set default values if not provided
        self.subreddits = self.config.get('subreddits', ['wallstreetbets', 'stocks', 'investing'])
        self.time_filter = self.config.get('timeframe', 'week')
        self.post_limit = self.config.get('post_limit', 100)

    def collect_data(self):
        """Collect data from specified subreddits"""
        all_posts = []
        
        for subreddit_name in self.subreddits:
            try:
                print(f"Collecting data from r/{subreddit_name}...")
                subreddit = self.reddit.subreddit(subreddit_name)
                
                # Test authentication
                subreddit.display_name  # This will raise an error if authentication fails
                
                # Get posts based on timeframe
                if self.time_filter == 'day':
                    posts = subreddit.top('day', limit=self.post_limit)
                elif self.time_filter == 'week':
                    posts = subreddit.top('week', limit=self.post_limit)
                elif self.time_filter == 'month':
                    posts = subreddit.top('month', limit=self.post_limit)
                else:
                    posts = subreddit.top('year', limit=self.post_limit)

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
                    
            except Exception as e:
                print(f"Error collecting data from r/{subreddit_name}: {str(e)}")
                continue
        
        if not all_posts:
            # Return empty DataFrame with expected columns
            return pd.DataFrame(columns=[
                'subreddit', 'title', 'selftext', 'score', 'comments',
                'created_utc', 'id', 'url'
            ])
            
        df = pd.DataFrame(all_posts)
        print(f"Debug - Collected {len(df)} posts total")
        print(f"Debug - DataFrame columns: {df.columns.tolist()}")
        return df 