FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY agent.py server.py ./
COPY docs ./docs
ENV PORT=8000
EXPOSE 8000
# Run as a non-root user and give the container no secrets except the API key.
RUN useradd -m app && chown -R app /app
USER app
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port $PORT"]
