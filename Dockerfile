FROM python:3.12-slim

WORKDIR /app

ARG REQUIREMENTS=requirements.txt
COPY requirements.txt requirements-nlp.txt ./
# For the NLP (worker) image, install CPU-only PyTorch first so the multi-GB
# CUDA/GPU wheels are never pulled (the deployment host is CPU-only).
RUN if [ "${REQUIREMENTS}" = "requirements-nlp.txt" ]; then \
        pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu; \
    fi && \
    pip install --no-cache-dir -r ${REQUIREMENTS}

COPY . .

# Default command — overridden per service in docker-compose.yml
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
