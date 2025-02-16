from praw import Reddit
import pandas as pd
import yaml
import os
from datetime import datetime, timedelta
import re
import time
from prawcore import Requestor, Authorizer
from prawcore.auth import ScriptAuthorizer, TrustedAuthenticator

class RedditDataCollector:
    def __init__(self, config):
        """Initialize with configuration dictionary"""
        print("\n=== Reddit Client Initialization ===")
        print("Environment Variables:")
        print(f"- NLTK_DATA: {os.getenv('NLTK_DATA')}")
        print(f"- APIFY_TOKEN exists: {bool(os.getenv('APIFY_TOKEN'))}")
        print(f"- APIFY_DEFAULT_KEY_VALUE_STORE_ID exists: {bool(os.getenv('APIFY_DEFAULT_KEY_VALUE_STORE_ID'))}")
        
        # Validate required fields
        required_fields = ['client_id', 'client_secret', 'user_agent']
        missing_fields = [field for field in required_fields if not config.get(field)]
        if missing_fields:
            raise ValueError(f"Missing required fields in config: {missing_fields}")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"\n=== Authentication Attempt {attempt + 1}/{max_retries} ===")
                print("Client Configuration:")
                print(f"- Client ID: {config['client_id']}")
                print(f"- User Agent: {config['user_agent']}")
                print(f"- Username: {config.get('redditUsername')}")
                
                # Set up the authenticator with proper OAuth2 flow
                requestor = Requestor(config['user_agent'], timeout=30)
                print("\nInitializing OAuth2 Flow:")
                print("1. Creating Requestor...")
                
                # Use TrustedAuthenticator instead of Authenticator
                authenticator = TrustedAuthenticator(
                    requestor,
                    config['client_id'],
                    config['client_secret']
                )
                print("2. TrustedAuthenticator created successfully")
                
                # Debug HTTP requests
                def log_request(request):
                    print(f"\nOutgoing Request:")
                    print(f"- Method: {request.method}")
                    print(f"- URL: {request.url}")
                    print(f"- Headers: {request.headers}")
                    return request

                requestor._http.hooks['request'] = [log_request]
                
                # Initialize Reddit instance directly with credentials
                print("\nCreating Reddit Instance:")
                self.reddit = Reddit(
                    client_id=config['client_id'],
                    client_secret=config['client_secret'],
                    user_agent=config['user_agent'],
                    requestor=requestor._http,
                    check_for_updates=False
                )
                
                print("\nTesting Authentication:")
                try:
                    subreddit = self.reddit.subreddit('announcements')
                    print("- Attempting to fetch a test post...")
                    next(subreddit.hot(limit=1))
                    print("✓ Authentication test successful")
                    
                    # Store configuration
                    self.config = config
                    self.subreddits = config.get('subreddits', [])
                    self.time_filter = config.get('timeframe', 'week')
                    self.post_limit = config.get('postLimit', 100)
                    
                    print("\nFinal Configuration:")
                    print(f"- Subreddits: {self.subreddits}")
                    print(f"- Time Filter: {self.time_filter}")
                    print(f"- Post Limit: {self.post_limit}")
                    return
                    
                except Exception as e:
                    print(f"\n⚠️ Authentication Test Failed:")
                    print(f"- Error Type: {type(e).__name__}")
                    print(f"- Error Message: {str(e)}")
                    if hasattr(e, 'response'):
                        print(f"- Status Code: {e.response.status_code}")
                        print(f"- Response Headers: {e.response.headers}")
                        print(f"- Response Body: {e.response.text}")
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
        print("\n=== Starting Data Collection ===")
        all_posts = []
        
        for subreddit_name in self.subreddits:
            print(f"\nProcessing r/{subreddit_name}:")
            try:
                print("1. Verifying Authentication:")
                print("- Checking token validity...")
                if hasattr(self.reddit.auth, 'access_token'):
                    print(f"- Access Token: {self.reddit.auth.access_token[:10]}...")
                
                print("\n2. Initializing Subreddit:")
                subreddit = self.reddit.subreddit(subreddit_name)
                print(f"- Subreddit object created: {subreddit}")
                
                print("\n3. Fetching Posts:")
                print(f"- Time Filter: {self.time_filter}")
                print(f"- Post Limit: {self.post_limit}")
                
                posts = []
                for post in subreddit.top(time_filter=self.time_filter, limit=self.post_limit):
                    print(f"\nProcessing Post {len(posts) + 1}/{self.post_limit}:")
                    print(f"- ID: {post.id}")
                    print(f"- Title: {post.title[:50]}...")
                    
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
                    
                print(f"\n✓ Successfully collected {len(posts)} posts from r/{subreddit_name}")
                all_posts.extend(posts)
                
            except Exception as e:
                print(f"\n❌ Error processing r/{subreddit_name}:")
                print(f"- Error Type: {type(e).__name__}")
                print(f"- Error Message: {str(e)}")
                if hasattr(e, 'response'):
                    print("HTTP Response Details:")
                    print(f"- Status Code: {e.response.status_code}")
                    print(f"- Headers: {e.response.headers}")
                    print(f"- Body: {e.response.text}")
                continue
        
        print("\n=== Data Collection Summary ===")
        print(f"- Total Posts Collected: {len(all_posts)}")
        print(f"- Subreddits Processed: {len(self.subreddits)}")
        
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