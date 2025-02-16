# Use multi-stage build
FROM python:3.12-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set up NLTK data directory
ENV NLTK_DATA=/usr/local/share/nltk_data
RUN mkdir -p $NLTK_DATA

# Download NLTK data with explicit verification
RUN python -c "import nltk; \
    nltk.download('punkt', download_dir='$NLTK_DATA'); \
    nltk.download('stopwords', download_dir='$NLTK_DATA'); \
    nltk.download('wordnet', download_dir='$NLTK_DATA'); \
    nltk.download('averaged_perceptron_tagger', download_dir='$NLTK_DATA'); \
    nltk.download('vader_lexicon', download_dir='$NLTK_DATA')"

# Verify NLTK data installation with proper path
RUN python -c "import nltk; \
    import os; \
    nltk.data.path.append('$NLTK_DATA'); \
    print('NLTK data path:', nltk.data.path); \
    print('VADER lexicon path:', os.path.join('$NLTK_DATA', 'sentiment/vader_lexicon.zip')); \
    assert os.path.exists(os.path.join('$NLTK_DATA', 'sentiment/vader_lexicon.zip')), 'VADER lexicon not found'; \
    print('VADER lexicon verified successfully')"

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Final stage
FROM python:3.12-slim

# Copy virtual environment
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set up NLTK data in final image
ENV NLTK_DATA=/usr/local/share/nltk_data
COPY --from=builder $NLTK_DATA $NLTK_DATA

# Set working directory
WORKDIR /usr/src/app

# Copy source code and configuration files
COPY . .

# Verify final setup
RUN python -c "import nltk; \
    import os; \
    nltk.data.path.append('$NLTK_DATA'); \
    print('Final NLTK data verification:'); \
    print('- NLTK data path:', nltk.data.path); \
    print('- VADER lexicon exists:', os.path.exists(os.path.join('$NLTK_DATA', 'sentiment/vader_lexicon.zip'))); \
    from nltk.sentiment.vader import SentimentIntensityAnalyzer; \
    sia = SentimentIntensityAnalyzer(); \
    print('VADER analyzer initialized successfully')"

# Run the actor
CMD ["python", "main.py"] 