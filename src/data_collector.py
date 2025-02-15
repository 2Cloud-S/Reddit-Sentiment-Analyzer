import praw
import pandas as pd
import yaml
from datetime import datetime
import os

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
        self.reddit = praw.Reddit(
            client_id=os.environ.get('REDDIT_CLIENT_ID'),
            client_secret=os.environ.get('REDDIT_CLIENT_SECRET'),
            user_agent=os.environ.get('REDDIT_USER_AGENT', 'SentimentAnalysis/1.0')
        )
        
        # Set default values if not provided
        self.subreddits = self.config.get('subreddits', ['wallstreetbets', 'stocks', 'investing'])
        self.time_filter = self.config.get('timeframe', 'week')
        self.post_limit = self.config.get('post_limit', 100)

    def collect_data(self):
        """Collect data from specified subreddits"""
        all_posts = []
        
        for subreddit_name in self.subreddits:
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                posts = subreddit.top(time_filter=self.time_filter, limit=self.post_limit)
                
                for post in posts:
                    post_data = {
                        'subreddit': subreddit_name,
                        'title': post.title,
                        'text': post.selftext,
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
        
        return pd.DataFrame(all_posts) 