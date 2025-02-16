from apify_client import ApifyClient
import os
import json
from src.data_collector import RedditDataCollector
from src.sentiment_analyzer import SentimentAnalyzer
from src.math_processor import MathProcessor
from src.visualizer import Visualizer
from src.topic_processor import TopicProcessor
from datetime import datetime
import re

def verify_nltk_setup():
    """Verify NLTK setup and VADER lexicon availability"""
    try:
        import nltk
        from nltk.sentiment.vader import SentimentIntensityAnalyzer
        
        print("\nVerifying NLTK setup:")
        print(f"- NLTK data path: {nltk.data.path}")
        
        # Try to initialize VADER
        sia = SentimentIntensityAnalyzer()
        test_result = sia.polarity_scores("This is a test sentence.")
        print("- VADER analyzer test:", test_result)
        print("✓ NLTK setup verified successfully")
        return True
    except Exception as e:
        print(f"❌ NLTK setup verification failed: {str(e)}")
        return False

def main():
    # Add near the start of main()
    if not verify_nltk_setup():
        raise RuntimeError("NLTK setup verification failed")
    
    # Initialize the Apify client
    client = ApifyClient(os.environ['APIFY_TOKEN'])
    
    try:
        # Get input
        print("Debug - Default KVS ID:", os.environ['APIFY_DEFAULT_KEY_VALUE_STORE_ID'])
        print("Debug - Default store initialized")
        
        # Get input from Apify
        default_store = client.key_value_store(os.environ['APIFY_DEFAULT_KEY_VALUE_STORE_ID'])
        input_record = default_store.get_record('INPUT')
        print("Debug - Raw input record:", input_record)
        
        input_data = input_record['value'] if input_record else {}
        print("Debug - Parsed input data:", {
            **input_data,
            'clientSecret': '[HIDDEN]' if 'clientSecret' in input_data else None
        })
        
        # Construct user agent from components
        reddit_username = input_data.get('redditUsername', '')
        app_name = input_data.get('appName', 'RedditSentimentAnalyzer')
        app_version = input_data.get('appVersion', 'v1.0')
        
        user_agent = f"script:{app_name}:{app_version} (by /u/{reddit_username})"
        print(f"Constructed user agent: {user_agent}")
        
        # Set Reddit credentials in environment variables
        os.environ['REDDIT_CLIENT_ID'] = str(input_data.get('clientId'))
        os.environ['REDDIT_CLIENT_SECRET'] = str(input_data.get('clientSecret'))
        os.environ['REDDIT_USER_AGENT'] = user_agent
        
        # Update config with input parameters
        config = {
            'subreddits': input_data.get('subreddits', ['wallstreetbets', 'stocks', 'investing']),
            'timeframe': input_data.get('timeframe', 'week'),
            'post_limit': input_data.get('postLimit', 100)
        }
        
        # Initialize components
        collector = RedditDataCollector(config)
        analyzer = SentimentAnalyzer()
        processor = MathProcessor()
        visualizer = Visualizer()
        
        try:
            # Process data
            print("Collecting Reddit data...")
            df = collector.collect_data()
            
            if df.empty:
                print("Warning: No data collected. Check your Reddit API credentials and subreddit names.")
                # Create minimal output
                output = {
                    'metrics': {},
                    'visualizations': [],
                    'analysis_summary': {
                        'total_posts_analyzed': 0,
                        'timeframe': config['timeframe'],
                        'subreddits_analyzed': config['subreddits'],
                        'error': 'No data collected. Possible authentication error.'
                    }
                }
            else:
                print("Analyzing sentiment...")
                df = analyzer.analyze_sentiment(df)
                
                print("Calculating metrics...")
                metrics = processor.calculate_metrics(df)
                
                # Generate visualizations
                print("Generating visualizations...")
                visualization_paths = []
                visualization_paths.append(visualizer.plot_sentiment_distribution(df))
                visualization_paths.append(visualizer.plot_engagement_vs_sentiment(df))
                visualization_paths.append(visualizer.plot_sentiment_time_series(df))
                visualization_paths.append(visualizer.plot_advanced_metrics(df))
                visualization_paths.append(visualizer.plot_emotion_distribution(df))
                visualization_paths.append(visualizer.plot_prediction_analysis(df))
                
                # Prepare output
                output = {
                    'metrics': metrics,
                    'visualizations': visualization_paths,
                    'analysis_summary': {
                        'total_posts_analyzed': len(df),
                        'timeframe': config['timeframe'],
                        'subreddits_analyzed': config['subreddits']
                    }
                }
            
            # Save output to the default store
            print("Saving output to key-value store...")
            try:
                default_store.set_record(
                    'OUTPUT',
                    output,
                    content_type='application/json'
                )
                print("Output saved successfully")
                
                # Save visualizations if they exist
                if 'visualizations' in output and output['visualizations']:
                    for i, viz_path in enumerate(output['visualizations']):
                        if os.path.exists(viz_path):
                            with open(viz_path, 'rb') as f:
                                viz_data = f.read()
                                default_store.set_record(
                                    f'visualization_{i}.png',
                                    viz_data,
                                    content_type='image/png'
                                )
                    print("Visualizations saved successfully")
                    
            except Exception as e:
                print(f"Error saving output: {str(e)}")
                # Create error output
                error_output = {
                    'error': str(e),
                    'status': 'failed',
                    'timestamp': datetime.now().isoformat()
                }
                default_store.set_record(
                    'ERROR',
                    error_output,
                    content_type='application/json'
                )
            
            print("Analysis complete! Check the output in Apify storage.")

        except Exception as e:
            print(f"Error in main processing: {str(e)}")
            raise

    except Exception as e:
        print(f"Error reading input: {str(e)}")
        input_data = {}
    
    # Validate Reddit credentials with debug logging
    client_id = input_data.get('clientId')
    client_secret = input_data.get('clientSecret')
    user_agent = input_data.get('userAgent', 'SentimentAnalysis/1.0')
    
    print("Debug - Final credentials state:")
    print(f"- Client ID: {'Present' if client_id else 'Missing'}")
    print(f"- Client Secret: {'Present' if client_secret else 'Missing'}")
    print(f"- User Agent: {user_agent}")
    
    if not client_id or not client_secret:
        raise ValueError(
            "Reddit API credentials are required. Please provide 'clientId' and 'clientSecret' "
            "in the input. You can get these from https://www.reddit.com/prefs/apps"
        )
    
    # Validate and format user agent
    if not re.match(r'^[a-zA-Z]+:[a-zA-Z0-9_-]+:v\d+\.\d+\s+\(by\s+/u/[a-zA-Z0-9_-]+\)$', user_agent):
        print("⚠️ Warning: User agent format does not match Reddit's requirements")
        print("Formatting user agent to match requirements...")
        user_agent = f"script:RedditSentimentAnalyzer:v1.0 (by /u/{user_agent.replace('/', '_')})"
        print(f"Updated user agent: {user_agent}")
    
    # Set Reddit credentials in environment variables
    os.environ['REDDIT_CLIENT_ID'] = str(client_id)
    os.environ['REDDIT_CLIENT_SECRET'] = str(client_secret)
    os.environ['REDDIT_USER_AGENT'] = user_agent
    
    # Update config with input parameters
    config = {
        'subreddits': input_data.get('subreddits', ['wallstreetbets', 'stocks', 'investing']),
        'timeframe': input_data.get('timeframe', 'week'),
        'post_limit': input_data.get('postLimit', 100)
    }
    
    # Initialize components
    collector = RedditDataCollector(config)
    analyzer = SentimentAnalyzer()
    processor = MathProcessor()
    visualizer = Visualizer()
    
    try:
        # Process data
        print("Collecting Reddit data...")
        df = collector.collect_data()
        
        if df.empty:
            print("Warning: No data collected. Check your Reddit API credentials and subreddit names.")
            # Create minimal output
            output = {
                'metrics': {},
                'visualizations': [],
                'analysis_summary': {
                    'total_posts_analyzed': 0,
                    'timeframe': config['timeframe'],
                    'subreddits_analyzed': config['subreddits'],
                    'error': 'No data collected. Possible authentication error.'
                }
            }
        else:
            print("Analyzing sentiment...")
            df = analyzer.analyze_sentiment(df)
            
            print("Calculating metrics...")
            metrics = processor.calculate_metrics(df)
            
            # Generate visualizations
            print("Generating visualizations...")
            visualization_paths = []
            visualization_paths.append(visualizer.plot_sentiment_distribution(df))
            visualization_paths.append(visualizer.plot_engagement_vs_sentiment(df))
            visualization_paths.append(visualizer.plot_sentiment_time_series(df))
            visualization_paths.append(visualizer.plot_advanced_metrics(df))
            visualization_paths.append(visualizer.plot_emotion_distribution(df))
            visualization_paths.append(visualizer.plot_prediction_analysis(df))
            
            # Prepare output
            output = {
                'metrics': metrics,
                'visualizations': visualization_paths,
                'analysis_summary': {
                    'total_posts_analyzed': len(df),
                    'timeframe': config['timeframe'],
                    'subreddits_analyzed': config['subreddits']
                }
            }
        
        # Save output to the default store
        print("Saving output to key-value store...")
        try:
            default_store.set_record(
                'OUTPUT',
                output,
                content_type='application/json'
            )
            print("Output saved successfully")
            
            # Save visualizations if they exist
            if 'visualizations' in output and output['visualizations']:
                for i, viz_path in enumerate(output['visualizations']):
                    if os.path.exists(viz_path):
                        with open(viz_path, 'rb') as f:
                            viz_data = f.read()
                            default_store.set_record(
                                f'visualization_{i}.png',
                                viz_data,
                                content_type='image/png'
                            )
                print("Visualizations saved successfully")
                
        except Exception as e:
            print(f"Error saving output: {str(e)}")
            # Create error output
            error_output = {
                'error': str(e),
                'status': 'failed',
                'timestamp': datetime.now().isoformat()
            }
            default_store.set_record(
                'ERROR',
                error_output,
                content_type='application/json'
            )
        
        print("Analysis complete! Check the output in Apify storage.")

    except Exception as e:
        print(f"Error in main processing: {str(e)}")
        raise

if __name__ == "__main__":
    main() 