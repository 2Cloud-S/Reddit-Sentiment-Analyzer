import praw
import pandas as pd
import yaml
from datetime import datetime
from tqdm import tqdm
import time

class RedditDataCollector:
    def __init__(self, config_path):
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        
        self.reddit = praw.Reddit(
            client_id=config['reddit']['client_id'],
            client_secret=config['reddit']['client_secret'],
            user_agent=config['reddit']['user_agent']
        )
        self.subreddits = config['subreddits']
        self.post_limit = config['data_collection']['post_limit']
        self.time_filter = config['data_collection']['time_filter']

    def collect_data(self):
        data = []
        
        for subreddit_name in tqdm(self.subreddits, desc="Collecting subreddit data"):
            subreddit = self.reddit.subreddit(subreddit_name)
            
            try:
                for post in tqdm(subreddit.top(time_filter=self.time_filter, limit=self.post_limit),
                               desc=f"Processing r/{subreddit_name}",
                               leave=False):
                    # Extract more data points
                    post_data = {
                        'subreddit': subreddit_name,
                        'title': post.title,
                        'text': post.selftext,
                        'score': post.score,
                        'comments': post.num_comments,
                        'created_utc': datetime.fromtimestamp(post.created_utc),
                        'upvote_ratio': post.upvote_ratio,
                        'is_original_content': post.is_original_content,
                        'over_18': post.over_18,
                        'spoiler': post.spoiler,
                        'stickied': post.stickied,
                        'url': post.url,
                        'author': str(post.author) if post.author else '[deleted]'
                    }
                    
                    # Add top-level comments data
                    post.comments.replace_more(limit=0)  # Remove MoreComments objects
                    comments_text = []
                    for comment in post.comments[:10]:  # Get top 10 comments
                        if comment.body:
                            comments_text.append(comment.body)
                    
                    post_data['top_comments'] = ' '.join(comments_text)
                    data.append(post_data)
                    
                    # Respect Reddit's API rate limits
                    time.sleep(0.5)
                    
            except Exception as e:
                print(f"Error collecting data from r/{subreddit_name}: {str(e)}")
                continue
        
        df = pd.DataFrame(data)
        
        # Add timestamp features
        df['hour'] = df['created_utc'].dt.hour
        df['day_of_week'] = df['created_utc'].dt.day_name()
        
        return df 