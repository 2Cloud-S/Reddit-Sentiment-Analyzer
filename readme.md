## 📊 Output Examples

The analyzer provides rich insights including:

- Sentiment distribution across subreddits
- Emotion analysis and trends
- Topic modeling results
- Engagement predictions
- Named entity recognition
- Advanced language metrics

Example visualizations:
![Sentiment Distribution](sentiment_distribution.png)
![Emotion Analysis](emotion_distribution.png)

## 🔑 API Credentials Setup

### Getting Reddit API Credentials

1. Go to [Reddit's App Preferences](https://www.reddit.com/prefs/apps)
2. Click "Create App" or "Create Another App"
3. Fill in the details:
   - Name: Your app name
   - Type: Select "script"
   - Description: Brief description
   - About URL: Your GitHub repo or website
   - Redirect URI: http://localhost:8080
4. Click "Create app"
5. Note down your:
   - Client ID (under your app name)
   - Client Secret (labeled as "secret")

### Using Credentials in Apify

When running the actor, provide your Reddit API credentials in the input:

json
{
"clientId": "your_client_id",
"clientSecret": "your_client_secret",
"username": "your_reddit_username",
"password": "your_reddit_password",
"userAgent": "SentimentAnalyzer/1.0",
"subreddits": ["wallstreetbets", "stocks"],
"timeframe": "week",
"postLimit": 100
}
Your credentials are securely stored and handled by Apify.

## 🔑 OAuth Authentication Setup

### Getting Reddit API OAuth Credentials

1. Go to [Reddit's App Preferences](https://www.reddit.com/prefs/apps)
2. Click "Create App" or "Create Another App"
3. Fill in the details:
   - Name: Your app name
   - Type: Select "script"
   - Description: Brief description
   - About URL: Your GitHub repo or website
   - Redirect URI: http://localhost:8080
4. Click "Create app"
5. Note down your:
   - Client ID (under your app name)
   - Client Secret (labeled as "secret")

### Required OAuth Credentials

The actor requires the following OAuth credentials:
- Client ID
- Client Secret
- Reddit Username
- Reddit Password
- User Agent (optional, default provided)

### Input Example with OAuth

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


## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

- **2Cloud-S** - *Initial work* - [GitHub](https://github.com/2Cloud-S)

## 🙏 Acknowledgments

- Reddit API for data access
- Apify for actor hosting
- NLTK and spaCy for NLP capabilities
- Hugging Face for transformer models

## 📞 Contact

- GitHub: [@2Cloud-S](https://github.com/2Cloud-S)
- Project Link: [https://github.com/2Cloud-S/reddit-sentiment-analyzer](https://github.com/2Cloud-S/reddit-sentiment-analyzer)