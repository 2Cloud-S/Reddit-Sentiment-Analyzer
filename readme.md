## 📊 Output Examples

The analyzer provides rich insights including:

- Sentiment distribution across subreddits
- Emotion analysis and trends
- Topic modeling results
- Engagement predictions
- Named entity recognition
- Advanced language metrics

Example visualizations:
![Sentiment Distribution](docs/images/sentiment_distribution.png)
![Emotion Analysis](docs/images/emotion_distribution.png)

## 🛠️ Technical Details

### Components

- **Data Collection**: Efficient Reddit data collection with rate limiting
- **Text Processing**: Advanced NLP pipeline with lemmatization and cleaning
- **Sentiment Analysis**: Hybrid approach combining rule-based and ML methods
- **Prediction Models**: RandomForest-based predictive analytics
- **Visualization**: Dynamic plotting with matplotlib and seaborn

### Machine Learning Models

- BERT-based sarcasm detection
- RandomForest sentiment predictor
- LDA topic modeling
- Engagement prediction model

## 📝 Input Schema
json
{
"subreddits": ["wallstreetbets", "stocks", "investing"],
"timeframe": "week",
"postLimit": 100,
"outputFormat": "json"
}

## 📈 Output Format
json
{
"metrics": {
"sentiment_metrics": {...},
"engagement_metrics": {...},
"topic_distribution": {...}
},
"visualizations": ["path/to/viz1.png", ...],
"analysis_summary": {...}
}
