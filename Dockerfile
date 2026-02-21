FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock* README.md* ./

RUN uv sync --frozen --no-dev

COPY main.py ./
COPY static/ ./static/
COPY sample_data/ ./sample_data/

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
