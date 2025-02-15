from textblob import TextBlob
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import pandas as pd
import numpy as np
from src.text_preprocessor import TextPreprocessor
from src.ner_processor import NERProcessor
from src.topic_processor import TopicProcessor
from src.sarcasm_detector import SarcasmDetector
from src.language_analyzer import LanguageAnalyzer
from src.prediction_analyzer import PredictionAnalyzer
import os
import spacy

class SentimentAnalyzer:
    def __init__(self):
        self.vader = SentimentIntensityAnalyzer()
        self.preprocessor = TextPreprocessor()
        
    def get_textblob_sentiment(self, text):
        if pd.isna(text) or text == '':
            return 0
        return TextBlob(text).sentiment.polarity
    
    def get_vader_sentiment(self, text):
        if pd.isna(text) or text == '':
            return 0
        scores = self.vader.polarity_scores(text)
        return scores['compound']
    
    def analyze_sentiment(self, df):
        """Analyze sentiment of Reddit posts"""
        if df.empty:
            print("Warning: Empty DataFrame received, skipping sentiment analysis")
            return df
        
        print("Preprocessing text...")
        try:
            # Create processed columns if data exists
            if 'title' in df.columns:
                df['processed_title'] = df['title'].apply(self.preprocessor.preprocess_text)
            else:
                df['processed_title'] = ''
            
            if 'selftext' in df.columns:
                df['processed_selftext'] = df['selftext'].apply(self.preprocessor.preprocess_text)
            else:
                df['processed_selftext'] = ''
            
            # TextBlob sentiment
            print("Calculating TextBlob sentiment...")
            df['title_sentiment_textblob'] = df['processed_title'].apply(self.get_textblob_sentiment)
            df['text_sentiment_textblob'] = df['processed_selftext'].apply(self.get_textblob_sentiment)
            
            # VADER sentiment
            print("Calculating VADER sentiment...")
            df['title_sentiment_vader'] = df['processed_title'].apply(self.get_vader_sentiment)
            df['text_sentiment_vader'] = df['processed_selftext'].apply(self.get_vader_sentiment)
            
            # Combined sentiment with weighted approach
            df['combined_sentiment_textblob'] = (
                df['title_sentiment_textblob'] * 0.3 +      # Title weight
                df['text_sentiment_textblob'] * 0.7         # Text weight - increased to total 1.0
            )
            
            df['combined_sentiment_vader'] = (
                df['title_sentiment_vader'] * 0.3 +         # Title weight
                df['text_sentiment_vader'] * 0.7            # Text weight - increased to total 1.0
            )
            
            # Final combined sentiment (average of TextBlob and VADER)
            df['combined_sentiment'] = (
                df['combined_sentiment_textblob'] * 0.5 +   # TextBlob weight
                df['combined_sentiment_vader'] * 0.5        # VADER weight
            )
            
            # Add NER analysis
            print("Performing Named Entity Recognition...")
            ner_processor = NERProcessor()
            df['title_entities'] = df['processed_title'].apply(ner_processor.extract_entities)
            df['text_entities'] = df['processed_selftext'].apply(ner_processor.extract_entities)
            
            # Add Topic Modeling
            print("Performing Topic Modeling...")
            topic_processor = TopicProcessor()
            corpus = topic_processor.prepare_texts(df['processed_selftext'].tolist())
            topic_processor.train_lda(corpus)
            df['document_topics'] = df['processed_selftext'].apply(topic_processor.get_document_topics)
            
            # Add Sarcasm Detection
            print("Detecting Sarcasm...")
            sarcasm_detector = SarcasmDetector()
            df['title_sarcasm'] = df['processed_title'].apply(sarcasm_detector.detect_sarcasm)
            df['text_sarcasm'] = df['processed_selftext'].apply(sarcasm_detector.detect_sarcasm)
            
            # Adjust sentiment based on sarcasm
            df['sarcasm_adjusted_sentiment'] = df['combined_sentiment'] * (1 - (df['title_sarcasm'] * 0.3 + df['text_sarcasm'] * 0.7))
            
            # Add Language Analysis
            print("Performing Language Analysis...")
            language_analyzer = LanguageAnalyzer()
            
            # Process title and text separately
            title_analysis = df['processed_title'].apply(language_analyzer.analyze_text)
            text_analysis = df['processed_selftext'].apply(language_analyzer.analyze_text)
            
            # Add metrics to DataFrame
            df['subjectivity'] = text_analysis.apply(lambda x: x['subjectivity'])
            df['readability_score'] = text_analysis.apply(lambda x: x['readability_score'])
            df['avg_sentence_length'] = text_analysis.apply(lambda x: x['avg_sentence_length'])
            df['formality_score'] = text_analysis.apply(lambda x: x['formality_score'])
            df['emotion_scores'] = text_analysis.apply(lambda x: x['emotion_scores'])
            df['stance'] = text_analysis.apply(lambda x: x['stance'])
            
            # Add Advanced Predictions
            print("Generating Advanced Predictions...")
            predictor = PredictionAnalyzer()
            predictor.train_models(df)
            predictions = predictor.predict_trends(df)
            
            # Add predictions to DataFrame
            df['predicted_sentiment'] = predictions['predicted_sentiment']
            df['predicted_engagement'] = predictions['predicted_engagement']
            df['trend_direction'] = predictions['trend_direction']
            
        except Exception as e:
            print(f"Error in sentiment analysis: {str(e)}")
            # Add empty sentiment columns
            df['sentiment_score'] = 0.0
            df['sentiment_label'] = 'neutral'
        
        return df 

def load_spacy_model():
    model_path = os.getenv('SPACY_MODEL_PATH', 'en_core_web_sm')
    return spacy.load(model_path) 