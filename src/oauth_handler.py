import praw
import prawcore
import os
from datetime import datetime, timedelta

class RedditOAuthHandler:
    def __init__(self, client_id, client_secret, username, password, user_agent):
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.password = password
        self.user_agent = user_agent
        self.reddit = None
        
    def authenticate(self):
        """Authenticate with Reddit using OAuth"""
        try:
            self.reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                username=self.username,
                password=self.password,
                user_agent=self.user_agent
            )
            # Verify authentication
            self.reddit.user.me()
            return self.reddit
        except prawcore.exceptions.OAuthException as e:
            raise Exception(f"OAuth authentication failed: {str(e)}")
        except Exception as e:
            raise Exception(f"Authentication error: {str(e)}")
