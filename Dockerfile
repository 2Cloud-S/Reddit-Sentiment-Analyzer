# Use multi-stage build
FROM python:3.12-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    iputils-ping \
    net-tools \
    ca-certificates \
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

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Final stage
FROM python:3.12-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    iputils-ping \
    net-tools \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

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

# Add logging configuration
ENV PYTHONUNBUFFERED=1

# Set DNS configuration
RUN echo "nameserver 8.8.8.8" > /etc/resolv.conf && \
    echo "nameserver 8.8.4.4" >> /etc/resolv.conf

# Verify network connectivity and DNS resolution
RUN echo "Testing network connectivity..." && \
    ping -c 1 8.8.8.8 || echo "Ping failed" && \
    curl -I https://old.reddit.com || echo "Curl failed" && \
    netstat -tulpn || echo "Netstat failed" && \
    python -c "import requests; print('Testing Reddit connection:', requests.get('https://old.reddit.com').status_code)"

# Update the verification script
RUN python -c "import nltk; \
    import os; \
    import logging; \
    logging.basicConfig(level=logging.DEBUG); \
    logger = logging.getLogger('Verification'); \
    logger.info('Starting verification...'); \
    nltk.data.path.append('$NLTK_DATA'); \
    logger.info('NLTK data path: %s', nltk.data.path); \
    logger.info('VADER lexicon exists: %s', os.path.exists(os.path.join('$NLTK_DATA', 'sentiment/vader_lexicon.zip'))); \
    from nltk.sentiment.vader import SentimentIntensityAnalyzer; \
    sia = SentimentIntensityAnalyzer(); \
    logger.info('VADER analyzer initialized successfully')"

# Run the actor
CMD ["python", "main.py"] 