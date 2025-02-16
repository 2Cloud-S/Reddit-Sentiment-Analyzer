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

# Download NLTK data with explicit vader_lexicon download
RUN python -c "import nltk; nltk.download(['punkt', 'stopwords', 'wordnet', 'averaged_perceptron_tagger']); nltk.download('vader_lexicon', download_dir='/usr/local/share/nltk_data')"

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Final stage
FROM python:3.12-slim

# Copy virtual environment
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy NLTK data with specific paths
COPY --from=builder /usr/local/share/nltk_data /usr/local/share/nltk_data
ENV NLTK_DATA=/usr/local/share/nltk_data

# Set working directory
WORKDIR /usr/src/app

# Copy source code and configuration files
COPY . .

# Ensure INPUT_SCHEMA.json is in the correct location
RUN test -f INPUT_SCHEMA.json || (echo "INPUT_SCHEMA.json is missing" && exit 1)
RUN test -f apify.json || (echo "apify.json is missing" && exit 1)

# Run the actor
CMD ["python", "main.py"] 