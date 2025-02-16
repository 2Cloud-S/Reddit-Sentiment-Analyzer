from praw import Reddit
import pandas as pd
import yaml
import os
from datetime import datetime, timedelta
import re
import time
from prawcore import Requestor, Authorizer
from prawcore.auth import ScriptAuthorizer, TrustedAuthenticator
import sys
import platform
import praw

class RedditDataCollector:
    def __init__(self, config):
        """Initialize with configuration dictionary"""
        print("\n=== Reddit Client Initialization ===")
        print("Environment Variables:")
        print(f"- NLTK_DATA: {os.getenv('NLTK_DATA')}")
        print(f"- APIFY_TOKEN exists: {bool(os.getenv('APIFY_TOKEN'))}")
        print(f"- APIFY_DEFAULT_KEY_VALUE_STORE_ID exists: {bool(os.getenv('APIFY_DEFAULT_KEY_VALUE_STORE_ID'))}")
        
        # Add timestamp to logs
        print(f"\nInitialization started at: {datetime.now().isoformat()}")
        
        # Validate required fields
        required_fields = ['client_id', 'client_secret', 'user_agent']
        missing_fields = [field for field in required_fields if not config.get(field)]
        if missing_fields:
            raise ValueError(f"Missing required fields in config: {missing_fields}")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"\n=== Authentication Attempt {attempt + 1}/{max_retries} ===")
                print(f"Timestamp: {datetime.now().isoformat()}")
                
                # Before OAuth Flow
                print("\n🔄 Pre-OAuth Flow Check:")
                print("- Validating credentials format...")
                print(f"- Client ID length: {len(config['client_id'])}")
                print(f"- Client Secret length: {len(config['client_secret'])}")
                print(f"- User Agent: {config['user_agent']}")
                
                # Before Authentication Request
                print("\n📡 Pre-Authentication Request:")
                print("- Preparing HTTP headers...")
                headers = {
                    'User-Agent': config['user_agent'],
                    'Accept': 'application/json'
                }
                print("- Headers prepared:", headers)
                
                # Set up the authenticator with proper OAuth2 flow
                requestor = Requestor(config['user_agent'], timeout=30)
                
                # Debug HTTP requests with detailed logging
                def log_request(request):
                    timestamp = datetime.now().isoformat()
                    print(f"\n🌐 Outgoing Request at {timestamp}:")
                    print(f"- Method: {request.method}")
                    print(f"- URL: {request.url}")
                    print(f"- Headers: {dict(request.headers)}")
                    if request.body:
                        print(f"- Body Length: {len(request.body)} bytes")
                    return request

                def log_response(response):
                    timestamp = datetime.now().isoformat()
                    print(f"\n📥 Response Received at {timestamp}:")
                    print(f"- Status Code: {response.status_code}")
                    print(f"- Headers: {dict(response.headers)}")
                    print(f"- Content Length: {len(response.content)} bytes")
                    try:
                        json_response = response.json()
                        print("- Response Type: JSON")
                        if 'error' in json_response:
                            print(f"- Error: {json_response['error']}")
                    except:
                        print("- Response Type: Non-JSON")
                    return response

                requestor._http.hooks['request'] = [log_request]
                requestor._http.hooks['response'] = [log_response]
                
                # Initialize Reddit instance
                print("\n🔐 Creating Reddit Instance:")
                print(f"Timestamp: {datetime.now().isoformat()}")
                self.reddit = Reddit(
                    client_id=config['client_id'],
                    client_secret=config['client_secret'],
                    user_agent=config['user_agent'],
                    requestor=requestor._http,
                    check_for_updates=False
                )
                
                # Test Authentication
                print("\n🔍 Testing Authentication:")
                try:
                    print("- Attempting to fetch test data...")
                    subreddit = self.reddit.subreddit('announcements')
                    test_post = next(subreddit.hot(limit=1))
                    print("✅ Authentication test successful")
                    print(f"- Test post ID: {test_post.id}")
                    print(f"- Test post title: {test_post.title[:50]}...")
                    
                    # Store configuration
                    self.config = config
                    self.subreddits = config.get('subreddits', [])
                    self.time_filter = config.get('timeframe', 'week')
                    self.post_limit = config.get('postLimit', 100)
                    
                    print("\n✨ Final Configuration:")
                    print(f"- Subreddits: {self.subreddits}")
                    print(f"- Time Filter: {self.time_filter}")
                    print(f"- Post Limit: {self.post_limit}")
                    print(f"- Setup completed at: {datetime.now().isoformat()}")
                    return
                    
                except Exception as e:
                    print(f"\n⚠️ Authentication Test Failed at {datetime.now().isoformat()}:")
                    print(f"- Error Type: {type(e).__name__}")
                    print(f"- Error Message: {str(e)}")
                    if hasattr(e, 'response'):
                        print("\n🔍 API Response Details:")
                        print(f"- Status Code: {e.response.status_code}")
                        print(f"- Response Headers: {dict(e.response.headers)}")
                        print(f"- Response Body: {e.response.text[:500]}...")
                    raise
                
            except Exception as e:
                print(f"\n❌ Authentication Attempt {attempt + 1} Failed:")
                print(f"Timestamp: {datetime.now().isoformat()}")
                print(f"- Error Type: {type(e).__name__}")
                print(f"- Error Message: {str(e)}")
                print("\n🔍 Debug Information:")
                print(f"- Python Version: {sys.version}")
                print(f"- PRAW Version: {praw.__version__}")
                print(f"- Operating System: {platform.system()} {platform.release()}")
                
                if attempt == max_retries - 1:
                    print("\n❌ All Authentication Attempts Failed")
                    print(f"Final Failure at: {datetime.now().isoformat()}")
                    raise ValueError(f"Failed to initialize Reddit client after {max_retries} attempts")
                
                print(f"\n⏳ Waiting for retry...")
                print(f"Next attempt in 2 seconds at: {(datetime.now() + timedelta(seconds=2)).isoformat()}")
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