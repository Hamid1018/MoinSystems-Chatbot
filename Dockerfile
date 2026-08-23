# Use the official lightweight Python 3.13 image
FROM python:3.13-slim

# Set the working directory
WORKDIR /app

# Set persistent cache path for Hugging Face models
ENV HF_HOME=/app/.cache/huggingface

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend code
COPY . .

# Pre-download the model during build so runtime never depends on outbound HF calls
# Replace 'all-MiniLM-L6-v2' with your specific model name if different
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Expose port 8000
EXPOSE 8000

# Run database migrations, then start the Uvicorn server
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000