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
        print("Collecting Reddit data...")
        all_posts = []
        
        for subreddit_name in self.subreddits:
            print(f"\nProcessing r/{subreddit_name}:")
            try:
                # Re-authenticate before accessing each subreddit
                print("- Re-authenticating...")
                self.reddit.auth.refresh()
                
                print("- Initializing subreddit connection...")
                subreddit = self.reddit.subreddit(subreddit_name)
                
                # Verify access with proper error handling
                try:
                    display_name = subreddit.display_name
                    print(f"✓ Connected to r/{subreddit_name}")
                except Exception as e:
                    print(f"❌ Failed to connect to r/{subreddit_name}: {str(e)}")
                    print("- Attempting to refresh authentication...")
                    self.reddit.auth.refresh()
                    continue
                
                print(f"- Fetching posts (limit: {self.post_limit}, timeframe: {self.time_filter})...")
                posts = []
                
                # Use proper listing endpoint with authentication check
                try:
                    for post in subreddit.top(time_filter=self.time_filter, limit=self.post_limit):
                        # Verify authentication for each batch
                        if not self.reddit.auth.validate_on_submit:
                            print("- Refreshing authentication token...")
                            self.reddit.auth.refresh()
                        
                        posts.append({
                            'subreddit': subreddit_name,
                            'title': post.title,
                            'selftext': post.selftext,
                            'score': post.score,
                            'num_comments': post.num_comments,
                            'created_utc': post.created_utc,
                            'id': post.id,
                            'url': post.url,
                            'author': str(post.author),
                            'upvote_ratio': post.upvote_ratio
                        })
                        print(f"  ✓ Collected post {len(posts)}/{self.post_limit}: {post.id}")
                    
                    print(f"✓ Successfully collected {len(posts)} posts from r/{subreddit_name}")
                    all_posts.extend(posts)
                    
                except Exception as e:
                    print(f"❌ Error fetching posts: {str(e)}")
                    print("- Error details:", {
                        'type': type(e).__name__,
                        'message': str(e),
                        'subreddit': subreddit_name
                    })
                    continue
                
            except Exception as e:
                print(f"\n❌ Error processing r/{subreddit_name}:")
                print(f"- Error type: {type(e).__name__}")
                print(f"- Error message: {str(e)}")
                continue
        
        print("\nData collection summary:")
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