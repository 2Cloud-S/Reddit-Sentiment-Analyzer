from apify_client import ApifyClient
import os
import logging
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
    # Set up logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    
    # Initialize the Apify client
    client = ApifyClient(os.environ['APIFY_TOKEN'])
    
    try:
        # Get input from Apify
        logger.debug("Getting input from Apify...")
        input_data = client.key_value_store().get_input() or {}
        
        if not input_data:
            raise ValueError("No input provided")
            
        # Construct user agent
        user_agent = f"script:{input_data.get('appName', 'RedditSentimentAnalyzer')}:v{input_data.get('appVersion', '1.0').lstrip('v')} (by /u/{input_data['redditUsername']})"
        
        # Create config from Apify input
        config = {
            'client_id': input_data['clientId'],
            'client_secret': input_data['clientSecret'],
            'user_agent': user_agent,
            'redditUsername': input_data['redditUsername'],
            'subreddits': input_data.get('subreddits', ['wallstreetbets']),
            'timeframe': input_data.get('timeframe', 'day'),
            'postLimit': input_data.get('postLimit', 2)
        }
        
        logger.debug(f"Configuration prepared (excluding secrets)")
        
        # Initialize collector and collect data
        collector = RedditDataCollector(config)
        data = collector.collect_data()
        
        # Store results in Apify dataset
        logger.debug(f"Storing {len(data)} posts in Apify dataset...")
        default_dataset = client.dataset()
        default_dataset.push_data({
            'post_count': len(data),
            'subreddits_analyzed': config['subreddits'],
            'timeframe': config['timeframe'],
            'data': data.to_dict('records')
        })
        
        logger.info("✓ Analysis complete and data stored")
        
    except Exception as e:
        logger.error(f"Error during execution: {str(e)}")
        raise

if __name__ == "__main__":
    main() 