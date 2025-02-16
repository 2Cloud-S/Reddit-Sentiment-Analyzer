from praw import Reddit
import pandas as pd
import yaml
import os
from datetime import datetime, timedelta
import re
import time
from prawcore import Requestor, Authenticator, ScriptAuthorizer
from prawcore.auth import BaseAuthenticator

class RedditDataCollector:
    def __init__(self, config):
        """Initialize with configuration dictionary"""
        print("Initializing RedditDataCollector...")
        
        # Validate required fields
        required_fields = ['client_id', 'client_secret', 'user_agent']
        missing_fields = [field for field in required_fields if not config.get(field)]
        if missing_fields:
            raise ValueError(f"Missing required fields in config: {missing_fields}")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"\nAttempt {attempt + 1} to initialize Reddit client:")
                print(f"- Client ID: {config['client_id']}")
                print(f"- User Agent: {config['user_agent']}")
                
                # Set up the authenticator with proper OAuth2 flow
                requestor = Requestor(config['user_agent'], timeout=30)
                authenticator = Authenticator(
                    requestor,
                    config['client_id'],
                    config['client_secret'],
                    redirect_uri='http://localhost:8080'
                )
                
                # Use ScriptAuthorizer for script-type apps
                authorizer = ScriptAuthorizer(
                    authenticator,
                    refresh_token=None,  # Not needed for script auth
                    username=config.get('redditUsername'),
                    password=None  # No password needed
                )
                
                # Initialize Reddit instance with the authorizer
                self.reddit = Reddit(
                    requestor=requestor._http,
                    authenticator=authenticator,
                    user_agent=config['user_agent'],
                    check_for_updates=False,
                    token_manager=authorizer
                )
                
                print("Testing authentication...")
                try:
                    # Test with read-only scope
                    subreddit = self.reddit.subreddit('announcements')
                    next(subreddit.hot(limit=1))
                    print("✓ Reddit API authentication successful")
                    
                    # Store configuration
                    self.config = config
                    self.subreddits = config.get('subreddits', [])
                    self.time_filter = config.get('timeframe', 'week')
                    self.post_limit = config.get('postLimit', 100)
                    
                    print("\nConfiguration loaded successfully")
                    return
                    
                except Exception as e:
                    print(f"⚠️ Read test failed: {str(e)}")
                    raise
                
            except Exception as e:
                print(f"\n⚠️ Authentication attempt {attempt + 1} failed:")
                print(f"- Error type: {type(e).__name__}")
                print(f"- Error message: {str(e)}")
                
                if 'invalid_grant' in str(e):
                    print("- Issue: Invalid credentials")
                    print("- Solution: Verify your client_id and client_secret")
                elif '401' in str(e):
                    print("- Issue: Unauthorized access")
                    print("- Solution: Check if your Reddit app is properly configured")
                    print("- Required app settings:")
                    print("  * Type: script")
                    print("  * Redirect URI: http://localhost:8080")
                
                if attempt == max_retries - 1:
                    raise ValueError(f"Failed to initialize Reddit client after {max_retries} attempts")
                
                print("Retrying in 2 seconds...")
                time.sleep(2)

    def collect_data(self):
        """Collect data from specified subreddits"""
        all_posts = []
        
        for subreddit_name in self.subreddits:
            try:
                print(f"\nProcessing r/{subreddit_name}:")
                print("- Initializing subreddit connection...")
                
                # Get subreddit instance with error handling
                try:
                    subreddit = self.reddit.subreddit(subreddit_name)
                    # Verify access by getting basic info
                    _ = subreddit.display_name
                    print(f"✓ Connected to r/{subreddit_name}")
                except Exception as e:
                    print(f"❌ Failed to connect to r/{subreddit_name}: {str(e)}")
                    continue
                
                print(f"- Fetching posts (limit: {self.post_limit}, timeframe: {self.time_filter})...")
                posts = []
                
                # Use proper listing endpoint with error handling
                try:
                    for post in subreddit.top(time_filter=self.time_filter, limit=self.post_limit):
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
                        print(f"- Collected post: {post.id}")
                except Exception as e:
                    print(f"❌ Error fetching posts: {str(e)}")
                    continue
                
                print(f"✓ Collected {len(posts)} posts from r/{subreddit_name}")
                all_posts.extend(posts)
                
            except Exception as e:
                print(f"\n❌ Error processing r/{subreddit_name}:")
                print(f"- Error type: {type(e).__name__}")
                print(f"- Error message: {str(e)}")
                continue
        
        return pd.DataFrame(all_posts) if all_posts else pd.DataFrame()

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