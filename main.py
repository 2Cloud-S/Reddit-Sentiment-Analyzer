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
    
    # Get input from the default key-value store
    default_store = client.key_value_store('default')
    input_data = default_store.get_record('INPUT').value if default_store.get_record('INPUT') else {}
    
    # Get configuration values
    subreddits = input_data.get('subreddits', ['wallstreetbets', 'stocks', 'investing'])
    timeframe = input_data.get('timeframe', 'week')
    post_limit = input_data.get('postLimit', 100)
    output_format = input_data.get('outputFormat', 'json')
    
    # Update config with input parameters
    config = {
        'subreddits': subreddits,
        'timeframe': timeframe,
        'post_limit': post_limit
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
            'timeframe': timeframe,
            'subreddits_analyzed': subreddits
        }
    }
    
    # Save output to the default store
    if output_format == 'json':
        default_store.set_record('OUTPUT', output)
    else:  # csv
        df.to_csv('output.csv', index=False)
        with open('output.csv', 'rb') as file:
            default_store.set_record('OUTPUT.csv', file.read())
    
    print("Analysis complete! Check the output in Apify storage.")

if __name__ == "__main__":
    main() 