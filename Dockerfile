# Use the official lightweight Python 3.13 image
FROM python:3.13-slim

# Set the working directory
WORKDIR /app

# Copy and install requirements securely
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend code
COPY . .

# Expose port 8000 for Koyeb
EXPOSE 8000

# Run database migrations, then start the Uvicorn server
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000