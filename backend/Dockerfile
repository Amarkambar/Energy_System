FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir fastapi uvicorn pymongo python-dotenv pydantic[email] \
    pandas numpy scikit-learn pyarrow requests python-dotenv

# Copy source
COPY . .

# Run FastAPI (not Streamlit) as the main service
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
