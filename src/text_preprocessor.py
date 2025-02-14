import re
import emoji
import contractions
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import nltk
import pandas as pd

class TextPreprocessor:
    def __init__(self):
        # Download required NLTK data
        try:
            nltk.download('punkt')
            nltk.download('stopwords')
            nltk.download('wordnet')
            nltk.download('averaged_perceptron_tagger')
        except:
            print("NLTK data already downloaded")
        
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        
    def preprocess_text(self, text):
        if pd.isna(text) or text == '':
            return ''
            
        # Convert to string if not already
        text = str(text)
        
        # Convert emojis to text
        text = emoji.demojize(text, delimiters=(" ", " "))
        
        # Expand contractions
        text = contractions.fix(text)
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove URLs
        text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
        
        # Remove punctuation
        text = re.sub(r'[^\w\s]', '', text)
        
        # Remove numbers
        text = re.sub(r'\d+', '', text)
        
        # Tokenization
        tokens = word_tokenize(text)
        
        # Remove stopwords and lemmatize
        tokens = [self.lemmatizer.lemmatize(token) 
                 for token in tokens 
                 if token not in self.stop_words]
        
        # Join tokens back into text
        processed_text = ' '.join(tokens)
        
        # Remove extra spaces
        processed_text = ' '.join(processed_text.split())
        
        return processed_text 