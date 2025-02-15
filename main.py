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
    
    try:
        # Get input using the correct method from Apify SDK
        default_kvs_id = os.environ.get('APIFY_DEFAULT_KEY_VALUE_STORE_ID')
        print(f"Debug - Default KVS ID: {default_kvs_id}")
        
        if not default_kvs_id:
            raise ValueError("APIFY_DEFAULT_KEY_VALUE_STORE_ID environment variable is not set")
            
        default_store = client.key_value_store(default_kvs_id)
        print("Debug - Default store initialized")
        
        # Get the input
        input_data = None
        try:
            input_record = default_store.get_record('INPUT')
            print(f"Debug - Raw input record: {input_record}")
            if input_record and hasattr(input_record, 'value'):
                input_data = input_record.value
        except Exception as e:
            print(f"Warning - Error getting input record: {str(e)}")
        
        # Ensure input_data is a dictionary
        input_data = input_data or {}
        
        print("Debug - Parsed input data:", {
            k: (v if k != 'clientSecret' else '[HIDDEN]') 
            for k, v in input_data.items()
        })
        
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
        default_store = client.key_value_store('default')
        default_store.set_record('OUTPUT', output)
    else:  # csv
        df.to_csv('output.csv', index=False)
        with open('output.csv', 'rb') as file:
            default_store.set_record('OUTPUT.csv', file.read())
    
    print("Analysis complete! Check the output in Apify storage.")

if __name__ == "__main__":
    main() 