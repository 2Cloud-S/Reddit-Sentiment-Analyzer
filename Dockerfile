FROM apify/actor-python:3.12

# Copy source code
COPY . ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK data and spaCy model
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('wordnet'); nltk.download('averaged_perceptron_tagger')"
RUN python -m spacy download en_core_web_sm

# Run the actor
CMD ["python", "main.py"] 