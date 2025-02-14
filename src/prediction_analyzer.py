from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

class PredictionAnalyzer:
    def __init__(self):
        self.sentiment_model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.engagement_model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        
    def prepare_features(self, df):
        """Prepare features for prediction"""
        features = pd.DataFrame()
        
        # Time-based features
        features['hour'] = df['created_utc'].dt.hour
        features['day_of_week'] = df['created_utc'].dt.dayofweek
        
        # Content-based features
        features['subjectivity'] = df['subjectivity']
        features['readability_score'] = df['readability_score']
        features['formality_score'] = df['formality_score']
        features['sarcasm_score'] = df['text_sarcasm']
        
        # Emotion features
        emotion_df = pd.DataFrame(df['emotion_scores'].tolist())
        features = pd.concat([features, emotion_df], axis=1)
        
        return self.scaler.fit_transform(features)
    
    def train_models(self, df):
        """Train prediction models"""
        X = self.prepare_features(df)
        
        # Train sentiment prediction model
        y_sentiment = df['combined_sentiment']
        self.sentiment_model.fit(X, y_sentiment)
        
        # Train engagement prediction model
        y_engagement = df['score'] * df['comments']  # Combined engagement metric
        self.engagement_model.fit(X, y_engagement)
        
    def predict_trends(self, df):
        """Predict sentiment and engagement trends"""
        X = self.prepare_features(df)
        
        predictions = {
            'predicted_sentiment': self.sentiment_model.predict(X),
            'predicted_engagement': self.engagement_model.predict(X),
            'sentiment_confidence': self.sentiment_model.predict_proba(X)[:, 1] if hasattr(self.sentiment_model, 'predict_proba') else None,
            'trend_direction': np.where(self.sentiment_model.predict(X) > df['combined_sentiment'].mean(), 'Positive', 'Negative')
        }
        
        return predictions 