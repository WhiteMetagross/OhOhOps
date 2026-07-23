FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-nodeps.txt ./

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip && \
    python -m pip install -r requirements.txt && \
    python -m pip install --no-deps -r requirements-nodeps.txt

RUN python -c "from tree_sitter_language_pack import get_parser; [get_parser(name) for name in ('python','javascript','typescript','tsx','c','cpp','go')]"


FROM base AS test

COPY requirements-dev.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install -r requirements-dev.txt
COPY . .
CMD ["python", "-m", "pytest", "-q"]


FROM base AS production

COPY app ./app
COPY scripts ./scripts
COPY runtime.txt ./

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=3)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
