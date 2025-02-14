import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd

class Visualizer:
    def __init__(self):
        # Use a built-in style instead of seaborn style
        plt.style.use('seaborn-v0_8-darkgrid')
        # Set the default figure size
        plt.rcParams['figure.figsize'] = [12, 6]
        # Improve font sizes
        plt.rcParams['font.size'] = 10
        plt.rcParams['axes.labelsize'] = 12
        plt.rcParams['axes.titlesize'] = 14
        
    def plot_sentiment_distribution(self, df):
        fig, ax = plt.subplots()
        sns.boxplot(x='subreddit', y='combined_sentiment', data=df, ax=ax)
        
        # Enhance the plot
        ax.set_title('Sentiment Distribution by Subreddit', pad=20)
        ax.set_xlabel('Subreddit')
        ax.set_ylabel('Sentiment Score')
        ax.tick_params(axis='x', rotation=45)
        
        # Add grid for better readability
        ax.grid(True, linestyle='--', alpha=0.7)
        
        plt.tight_layout()
        path = 'sentiment_distribution.png'
        plt.savefig(path, dpi=300, bbox_inches='tight')
        plt.close()
        return path
    
    def plot_engagement_vs_sentiment(self, df):
        fig, ax = plt.subplots()
        
        # Create scatter plot with improved aesthetics
        scatter = sns.scatterplot(
            data=df,
            x='combined_sentiment',
            y='comments',
            hue='subreddit',
            size='score',
            sizes=(50, 400),
            alpha=0.6,
            ax=ax
        )
        
        # Enhance the plot
        ax.set_title('Engagement vs Sentiment by Subreddit', pad=20)
        ax.set_xlabel('Sentiment Score')
        ax.set_ylabel('Number of Comments')
        
        # Add grid
        ax.grid(True, linestyle='--', alpha=0.3)
        
        # Improve legend
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0)
        
        # Add trend line for each subreddit
        for subreddit in df['subreddit'].unique():
            subreddit_data = df[df['subreddit'] == subreddit]
            z = np.polyfit(subreddit_data['combined_sentiment'], subreddit_data['comments'], 1)
            p = np.poly1d(z)
            ax.plot(subreddit_data['combined_sentiment'], 
                   p(subreddit_data['combined_sentiment']), 
                   linestyle='--', alpha=0.5)
        
        plt.tight_layout()
        path = 'engagement_vs_sentiment.png'
        plt.savefig(path, dpi=300, bbox_inches='tight')
        plt.close()
        return path
    
    def plot_sentiment_time_series(self, df):
        """New method to plot sentiment over time"""
        fig, ax = plt.subplots()
        
        for subreddit in df['subreddit'].unique():
            subreddit_data = df[df['subreddit'] == subreddit]
            subreddit_data = subreddit_data.sort_values('created_utc')
            
            ax.plot(subreddit_data['created_utc'], 
                   subreddit_data['combined_sentiment'], 
                   label=subreddit,
                   marker='o',
                   markersize=4,
                   alpha=0.6)
        
        ax.set_title('Sentiment Trends Over Time', pad=20)
        ax.set_xlabel('Date')
        ax.set_ylabel('Sentiment Score')
        ax.grid(True, linestyle='--', alpha=0.3)
        ax.legend()
        
        # Rotate x-axis dates for better readability
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        path = 'sentiment_time_series.png'
        plt.savefig(path, dpi=300, bbox_inches='tight')
        plt.close()
        return path
    
    def plot_sentiment_comparison(self, df):
        """Plot comparison between VADER and TextBlob sentiments"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
        
        # VADER vs TextBlob scatter plot
        sns.scatterplot(
            data=df,
            x='combined_sentiment_vader',
            y='combined_sentiment_textblob',
            hue='subreddit',
            alpha=0.6,
            ax=ax1
        )
        
        # Add diagonal line for reference
        lims = [
            min(ax1.get_xlim()[0], ax1.get_ylim()[0]),
            max(ax1.get_xlim()[1], ax1.get_ylim()[1])
        ]
        ax1.plot(lims, lims, '--', color='gray', alpha=0.5)
        
        ax1.set_title('VADER vs TextBlob Sentiment Comparison')
        ax1.set_xlabel('VADER Sentiment')
        ax1.set_ylabel('TextBlob Sentiment')
        ax1.grid(True, linestyle='--', alpha=0.3)
        
        # Sentiment distribution comparison
        df_melted = pd.melt(
            df,
            value_vars=['combined_sentiment_vader', 'combined_sentiment_textblob'],
            var_name='Analyzer',
            value_name='Sentiment'
        )
        # Add subreddit information to melted dataframe
        df_melted['subreddit'] = df_melted.index.map(df['subreddit'])
        
        # Create violin plot with correct parameters
        sns.violinplot(
            data=df_melted,
            x='Analyzer',
            y='Sentiment',
            hue='subreddit',
            split=False,  # Changed to False for better visualization
            ax=ax2
        )
        
        ax2.set_title('Sentiment Distribution Comparison')
        ax2.set_xlabel('Analyzer')
        ax2.set_ylabel('Sentiment Score')
        ax2.tick_params(axis='x', rotation=45)
        
        # Adjust legend
        ax2.legend(title='Subreddit', bbox_to_anchor=(1.05, 1), loc='upper left')
        
        plt.tight_layout()
        path = 'sentiment_comparison.png'
        plt.savefig(path, dpi=300, bbox_inches='tight')
        plt.close()
        return path

    def plot_entity_distribution(self, df):
        """Plot distribution of top entities across subreddits"""
        all_entities = []
        for entities in df['text_entities']:
            all_entities.extend([e['text'] for e in entities])
        
        top_entities = pd.Series(all_entities).value_counts().head(10)
        
        fig, ax = plt.subplots(figsize=(12, 6))
        top_entities.plot(kind='bar', ax=ax)
        
        ax.set_title('Top Named Entities Across All Subreddits')
        ax.set_xlabel('Entity')
        ax.set_ylabel('Frequency')
        plt.xticks(rotation=45, ha='right')
        
        plt.tight_layout()
        path = 'entity_distribution.png'
        plt.savefig(path, dpi=300, bbox_inches='tight')
        plt.close()
        return path

    def plot_topic_distribution(self, df, topic_labels):
        """Enhanced topic distribution plot with labels"""
        topic_dists = []
        for topics in df['document_topics']:
            dist = [0] * 5
            for topic_id, prob in topics:
                dist[topic_id] = prob
            topic_dists.append(dist)
        
        topic_df = pd.DataFrame(topic_dists, columns=topic_labels)
        topic_df['subreddit'] = df['subreddit']
        
        fig, ax = plt.subplots(figsize=(15, 8))
        topic_df.groupby('subreddit').mean().plot(kind='bar', ax=ax)
        
        ax.set_title('Topic Distribution by Subreddit')
        ax.set_xlabel('Subreddit')
        ax.set_ylabel('Topic Probability')
        plt.legend(title='Topics', bbox_to_anchor=(1.05, 1))
        
        plt.tight_layout()
        path = 'topic_distribution.png'
        plt.savefig(path, dpi=300, bbox_inches='tight')
        plt.close()
        return path

    def plot_advanced_metrics(self, df):
        """Plot advanced language metrics"""
        metrics_to_plot = [
            'subjectivity', 'readability_score', 
            'avg_sentence_length', 'formality_score'
        ]
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        axes = axes.ravel()
        
        for idx, metric in enumerate(metrics_to_plot):
            if metric in df.columns:  # Check if metric exists in DataFrame
                sns.boxplot(
                    x='subreddit',
                    y=metric,
                    data=df,
                    ax=axes[idx]
                )
                axes[idx].set_title(f'{metric.replace("_", " ").title()} by Subreddit')
                axes[idx].tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        path = 'advanced_metrics.png'
        plt.savefig(path, dpi=300, bbox_inches='tight')
        plt.close()
        return path

    def plot_emotion_distribution(self, df):
        """Plot emotion distribution across subreddits"""
        emotions_df = pd.DataFrame(df['emotion_scores'].tolist())
        emotions_df['subreddit'] = df['subreddit']
        
        fig, ax = plt.subplots(figsize=(12, 6))
        emotions_df.groupby('subreddit').mean().plot(kind='bar', ax=ax)
        
        ax.set_title('Emotion Distribution by Subreddit')
        ax.set_xlabel('Subreddit')
        ax.set_ylabel('Average Emotion Score')
        plt.legend(title='Emotions', bbox_to_anchor=(1.05, 1))
        
        plt.tight_layout()
        path = 'emotion_distribution.png'
        plt.savefig(path, dpi=300, bbox_inches='tight')
        plt.close()
        return path

    def plot_prediction_analysis(self, df):
        """Plot prediction analysis and trends"""
        fig, axes = plt.subplots(2, 1, figsize=(15, 12))
        
        # Sentiment Predictions vs Actual
        axes[0].scatter(df['combined_sentiment'], df['predicted_sentiment'], alpha=0.5)
        axes[0].plot([df['combined_sentiment'].min(), df['combined_sentiment'].max()], 
                     [df['combined_sentiment'].min(), df['combined_sentiment'].max()], 
                     'r--', label='Perfect Prediction')
        axes[0].set_xlabel('Actual Sentiment')
        axes[0].set_ylabel('Predicted Sentiment')
        axes[0].set_title('Sentiment Prediction Analysis')
        axes[0].legend()
        
        # Engagement Predictions by Subreddit
        sns.boxplot(x='subreddit', y='predicted_engagement', 
                    hue='trend_direction', data=df, ax=axes[1])
        axes[1].set_title('Predicted Engagement by Subreddit and Trend')
        axes[1].tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        path = 'prediction_analysis.png'
        plt.savefig(path, dpi=300, bbox_inches='tight')
        plt.close()
        return path