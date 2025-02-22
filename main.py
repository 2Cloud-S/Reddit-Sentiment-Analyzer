from apify_client import ApifyClient
import os
import json
import asyncio
from src.data_collector import RedditDataCollector

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
        
        # Continue with the rest of your processing...
        
    except Exception as e:
        print(f"Error in main processing: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())