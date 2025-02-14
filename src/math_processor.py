import numpy as np
from scipy import stats

class MathProcessor:
    def calculate_metrics(self, df):
        metrics = {}
        
        for subreddit in df['subreddit'].unique():
            subreddit_data = df[df['subreddit'] == subreddit]
            
            # Calculate advanced metrics
            metrics[subreddit] = {
                'sentiment_mean': subreddit_data['combined_sentiment'].mean(),
                'sentiment_std': subreddit_data['combined_sentiment'].std(),
                'sentiment_skew': stats.skew(subreddit_data['combined_sentiment']),
                'sentiment_kurtosis': stats.kurtosis(subreddit_data['combined_sentiment']),
                'engagement_score': self._calculate_engagement_score(subreddit_data),
                'volatility': self._calculate_volatility(subreddit_data)
            }
        
        return metrics
    
    def _calculate_engagement_score(self, df):
        # Normalized engagement score based on comments and score
        normalized_comments = (df['comments'] - df['comments'].min()) / (df['comments'].max() - df['comments'].min())
        normalized_score = (df['score'] - df['score'].min()) / (df['score'].max() - df['score'].min())
        
        return (normalized_comments * 0.5 + normalized_score * 0.5).mean()
    
    def _calculate_volatility(self, df):
        # Calculate sentiment volatility using rolling standard deviation
        return df['combined_sentiment'].rolling(window=5).std().mean() 