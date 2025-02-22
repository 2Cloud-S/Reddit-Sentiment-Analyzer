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
import asyncio

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

async def main():
    client = ApifyClient(os.environ['APIFY_TOKEN'])
    
    try:
        # Get input from Apify
        default_store = client.key_value_store(os.environ['APIFY_DEFAULT_KEY_VALUE_STORE_ID'])
        input_record = default_store.get_record('INPUT')
        
        if not input_record or not input_record.get('value'):
            raise ValueError("No input provided")
            
        input_data = input_record['value']
        
        # Initialize collector with input configuration
        collector = RedditDataCollector(input_data)
        
        # Collect and process data
        print("Collecting Reddit data...")
        df = await collector.collect_data()
        
        # Clean up resources
        await collector.cleanup()
        
        if df.empty:
            print("Warning: No data collected")
            output = {
                'metrics': {},
                'visualizations': [],
                'analysis_summary': {
                    'total_posts_analyzed': 0,
                    'timeframe': input_data['timeframe'],
                    'subreddits_analyzed': input_data['subreddits'],
                    'error': 'No data collected'
                }
            }
        else:
            print("Analyzing sentiment...")
            analyzer = SentimentAnalyzer()
            df = analyzer.analyze_sentiment(df)
            
            print("Calculating metrics...")
            processor = MathProcessor()
            metrics = processor.calculate_metrics(df)
            
            # Generate visualizations
            print("Generating visualizations...")
            visualizer = Visualizer()
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
                    'timeframe': input_data['timeframe'],
                    'subreddits_analyzed': input_data['subreddits']
                }
            }
        
        # Save output to key-value store
        print("Saving output to key-value store...")
        default_store.set_record(
            'OUTPUT',
            output,
            content_type='application/json'
        )
        print("Output saved successfully")
        
        print("Analysis complete! Check the output in Apify storage.")
        
    except Exception as e:
        print(f"Error in main processing: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 