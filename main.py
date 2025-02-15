from apify_client import ApifyClient
import os
import json
from src.data_collector import RedditDataCollector
from src.sentiment_analyzer import SentimentAnalyzer
from src.math_processor import MathProcessor
from src.visualizer import Visualizer
from src.topic_processor import TopicProcessor

def main():
    # Initialize the Apify client
    client = ApifyClient(os.environ['APIFY_TOKEN'])
    
    # Get input from the default key-value store with enhanced debug logging
    default_store = client.key_value_store('default')
    print("Debug - Default store:", default_store)
    
    try:
        input_record = default_store.get_record('INPUT')
        print("Debug - Raw input record:", input_record)
        
        if input_record is None:
            print("Warning: Input record is None. Checking for direct environment variables...")
            # Try to get credentials from environment variables as fallback
            input_data = {
                'clientId': os.environ.get('REDDIT_CLIENT_ID'),
                'clientSecret': os.environ.get('REDDIT_CLIENT_SECRET'),
                'userAgent': os.environ.get('REDDIT_USER_AGENT', 'SentimentAnalysis/1.0'),
                'subreddits': os.environ.get('REDDIT_SUBREDDITS', '["wallstreetbets","stocks","investing"]'),
                'timeframe': os.environ.get('REDDIT_TIMEFRAME', 'week'),
                'postLimit': int(os.environ.get('REDDIT_POST_LIMIT', '100'))
            }
        else:
            input_data = input_record.value if input_record else {}
        
        print("Debug - Parsed input data:", {
            k: (v if k != 'clientSecret' else '[HIDDEN]') 
            for k, v in input_data.items()
        })
        
    except Exception as e:
        print(f"Error reading input: {str(e)}")
        raise
    
    # Validate Reddit credentials with debug logging
    client_id = input_data.get('clientId')
    client_secret = input_data.get('clientSecret')
    user_agent = input_data.get('userAgent', 'SentimentAnalysis/1.0')
    
    print("Debug - Credentials:")
    print(f"- Client ID: {'Present' if client_id else 'Missing'}")
    print(f"- Client Secret: {'Present' if client_secret else 'Missing'}")
    print(f"- User Agent: {user_agent}")
    
    if not client_id or not client_secret:
        raise ValueError(
            "Reddit API credentials are required. Please provide 'clientId' and 'clientSecret' "
            "in the input. You can get these from https://www.reddit.com/prefs/apps"
        )
    
    # Set Reddit credentials in environment variables
    os.environ['REDDIT_CLIENT_ID'] = str(client_id)
    os.environ['REDDIT_CLIENT_SECRET'] = str(client_secret)
    os.environ['REDDIT_USER_AGENT'] = str(user_agent)
    
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
    
    # Process data
    print("Collecting Reddit data...")
    df = collector.collect_data()
    
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
    output_format = input_data.get('outputFormat', 'json')
    if output_format == 'json':
        default_store.set_record('OUTPUT', output)
    else:  # csv
        df.to_csv('output.csv', index=False)
        with open('output.csv', 'rb') as file:
            default_store.set_record('OUTPUT.csv', file.read())
    
    print("Analysis complete! Check the output in Apify storage.")

if __name__ == "__main__":
    main() 