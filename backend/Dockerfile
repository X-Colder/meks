FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple uv

COPY pyproject.toml .
RUN uv pip install --system --index-url https://pypi.tuna.tsinghua.edu.cn/simple -e "." --target /install

FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r meks && useradd -r -g meks -d /app -s /sbin/nologin meks

WORKDIR /app

COPY --from=builder /install /usr/local/lib/python3.11/site-packages/
COPY --chown=meks:meks . .

USER meks

EXPOSE 8000

CMD ["uvicorn", "meks.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
