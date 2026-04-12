FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for PuLP/CBC solver
RUN apt-get update && \
    apt-get install -y --no-install-recommends coinor-cbc && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY src/ src/
COPY examples/ examples/
COPY README.md .

RUN pip install --no-cache-dir -e .

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "src/viz/app.py", \
            "--server.port=8501", \
            "--server.address=0.0.0.0", \
            "--server.headless=true"]
