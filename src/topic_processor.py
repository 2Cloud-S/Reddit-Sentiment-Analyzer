from gensim import corpora, models
from gensim.models.coherencemodel import CoherenceModel
import numpy as np

class TopicProcessor:
    def __init__(self, num_topics=5):
        self.num_topics = num_topics
        self.dictionary = None
        self.lda_model = None
        self.texts = []
        
    def prepare_texts(self, texts):
        # Convert texts to document-term matrix
        texts = [[word for word in text.split()] for text in texts if text.strip()]
        self.dictionary = corpora.Dictionary(texts)
        corpus = [self.dictionary.doc2bow(text) for text in texts]
        self.texts = texts
        return corpus
    
    def train_lda(self, corpus):
        # Train LDA model with improved parameters
        self.lda_model = models.LdaModel(
            corpus=corpus,
            id2word=self.dictionary,
            num_topics=self.num_topics,
            random_state=42,
            update_every=1,
            chunksize=100,
            passes=20,  # Increased passes
            alpha='auto',
            per_word_topics=True,
            minimum_probability=0.01  # Filter low probability topics
        )
        
        # Calculate topic coherence
        self.coherence_model = CoherenceModel(
            model=self.lda_model,
            texts=self.texts,
            dictionary=self.dictionary,
            coherence='c_v'
        )
        self.coherence_score = self.coherence_model.get_coherence()

    def get_document_topics(self, text):
        if not self.lda_model or not self.dictionary:
            return []
        
        bow = self.dictionary.doc2bow(text.split())
        return self.lda_model.get_document_topics(bow)
    
    def get_topic_terms(self, num_words=10):
        if not self.lda_model:
            return []
        
        return [self.lda_model.show_topic(i, num_words) for i in range(self.num_topics)]

    def get_topic_labels(self):
        """Generate descriptive labels for topics"""
        labels = []
        for topic_id in range(self.num_topics):
            top_words = [word for word, _ in self.lda_model.show_topic(topic_id, topn=5)]
            label = f"Topic {topic_id + 1}: {', '.join(top_words)}"
            labels.append(label)
        return labels 