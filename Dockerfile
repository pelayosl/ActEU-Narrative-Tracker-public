FROM python:3.13-slim

WORKDIR /app

ARG REQUIREMENTS=requirements.txt
COPY requirements.txt requirements-nlp.txt ./
RUN pip install --no-cache-dir -r ${REQUIREMENTS}

COPY . .

# Default command — overridden per service in docker-compose.yml
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
