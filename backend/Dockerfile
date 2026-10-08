FROM python:3.12-slim

WORKDIR /app

# Install the declared runtime dependencies (the API imports joblib and the ML
# stack directly; maintaining a second partial dependency list caused startup failures).
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --shell /usr/sbin/nologin appuser

COPY . .
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
