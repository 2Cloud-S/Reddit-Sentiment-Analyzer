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

# Download NLTK data
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('wordnet'); nltk.download('averaged_perceptron_tagger')"

# Download spaCy model
RUN python -m spacy download en_core_web_sm && \
    mkdir -p /opt/spacy_models && \
    ln -s /opt/venv/lib/python3.12/site-packages/en_core_web_sm /opt/spacy_models/en_core_web_sm

# Final stage
FROM python:3.12-slim

# Copy virtual environment
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy NLTK data
COPY --from=builder /root/nltk_data /root/nltk_data

# Copy spaCy models
COPY --from=builder /opt/spacy_models /opt/spacy_models
ENV SPACY_MODEL_PATH=/opt/spacy_models/en_core_web_sm

# Set working directory
WORKDIR /usr/src/app

# Copy source code and input schema
COPY . .
COPY INPUT_SCHEMA.json /usr/src/app/INPUT_SCHEMA.json

# Run the actor
CMD ["python", "main.py"] 