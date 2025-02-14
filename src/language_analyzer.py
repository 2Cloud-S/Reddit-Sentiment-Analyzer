from textblob import TextBlob
from nltk.tokenize import sent_tokenize
import spacy
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import textstat
import numpy as np

class LanguageAnalyzer:
    def __init__(self):
        self.nlp = spacy.load('en_core_web_sm')
        self.vader = SentimentIntensityAnalyzer()
        
    def analyze_text(self, text):
        if not text:
            return self._get_empty_metrics()
            
        doc = self.nlp(text)
        blob = TextBlob(text)
        
        return {
            'subjectivity': blob.sentiment.subjectivity,
            'readability_score': textstat.flesch_reading_ease(text),
            'avg_sentence_length': np.mean([len(sent.split()) for sent in sent_tokenize(text)]),
            'formality_score': self._calculate_formality(doc),
            'emotion_scores': self._get_emotion_scores(text),
            'stance': self._detect_stance(doc)
        }
    
    def _calculate_formality(self, doc):
        formal_pos = ['NOUN', 'ADJ', 'ADP', 'DET']
        informal_pos = ['INTJ', 'PRON', 'ADV']
        
        formal_count = sum(1 for token in doc if token.pos_ in formal_pos)
        informal_count = sum(1 for token in doc if token.pos_ in informal_pos)
        total = formal_count + informal_count
        
        return formal_count / total if total > 0 else 0.5
    
    def _get_emotion_scores(self, text):
        # Basic emotion lexicon
        emotions = {
            'joy': ['happy', 'great', 'excellent', 'good', 'positive'],
            'anger': ['angry', 'mad', 'furious', 'negative', 'bad'],
            'fear': ['scared', 'afraid', 'worried', 'concerned'],
            'surprise': ['wow', 'unexpected', 'surprised', 'shocking']
        }
        
        scores = {}
        text_lower = text.lower()
        for emotion, words in emotions.items():
            score = sum(text_lower.count(word) for word in words)
            scores[emotion] = score
            
        return scores
    
    def _detect_stance(self, doc):
        agreement_markers = ['agree', 'yes', 'correct', 'right', 'true']
        disagreement_markers = ['disagree', 'no', 'wrong', 'false', 'incorrect']
        
        text_lower = doc.text.lower()
        agreement_score = sum(text_lower.count(word) for word in agreement_markers)
        disagreement_score = sum(text_lower.count(word) for word in disagreement_markers)
        
        if agreement_score > disagreement_score:
            return 'agreement'
        elif disagreement_score > agreement_score:
            return 'disagreement'
        return 'neutral'
    
    def _get_empty_metrics(self):
        return {
            'subjectivity': 0.0,
            'readability_score': 0.0,
            'avg_sentence_length': 0.0,
            'formality_score': 0.5,
            'emotion_scores': {
                'joy': 0, 'anger': 0, 'fear': 0, 'surprise': 0
            },
            'stance': 'neutral'
        } 