import spacy
from collections import Counter
import pandas as pd

class NERProcessor:
    def __init__(self):
        # Load English language model
        try:
            self.nlp = spacy.load('en_core_web_sm')
        except:
            import subprocess
            subprocess.run(['python', '-m', 'spacy', 'download', 'en_core_web_sm'])
            self.nlp = spacy.load('en_core_web_sm')
    
    def extract_entities(self, text):
        if pd.isna(text) or text == '':
            return []
        
        doc = self.nlp(str(text))
        entities = []
        
        for ent in doc.ents:
            entities.append({
                'text': ent.text,
                'label': ent.label_,
                'start': ent.start_char,
                'end': ent.end_char
            })
        
        return entities
    
    def get_entity_frequencies(self, entities_list):
        entity_counter = Counter()
        for entities in entities_list:
            for entity in entities:
                entity_counter[f"{entity['text']} ({entity['label']})"] += 1
        return dict(entity_counter.most_common()) 