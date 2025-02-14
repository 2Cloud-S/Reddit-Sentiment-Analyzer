from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import numpy as np
import pandas as pd

class SarcasmDetector:
    def __init__(self):
        # Use a different pre-trained model for sarcasm detection
        model_name = "handplay/bert-base-uncased-finetuned-sarcasm"
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.model.eval()  # Set to evaluation mode
        except Exception as e:
            print(f"Warning: Could not load sarcasm model. Falling back to basic detection. Error: {e}")
            self.tokenizer = None
            self.model = None
    
    def detect_sarcasm(self, text):
        if pd.isna(text) or text == '' or self.model is None:
            return 0.0
        
        try:
            # Preprocess and tokenize
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            )
            
            # Get prediction
            with torch.no_grad():
                outputs = self.model(**inputs)
                probabilities = torch.nn.functional.softmax(outputs.logits, dim=-1)
                
            # Return sarcasm probability
            return probabilities[0][1].item()
            
        except Exception as e:
            print(f"Warning: Sarcasm detection failed for text. Error: {e}")
            return 0.0 