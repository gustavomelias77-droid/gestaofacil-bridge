FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
  libnss3 libnspr4 libatk-bridge2.0-0 libdrm2 libxkbcommon0 \
  libxcomposite1 libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 \
  libcairo2 libasound2 libatspi2.0-0 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt app.py ./

RUN pip install --no-cache-dir -r requirements.txt && \
    playwright install chromium && \
    playwright install-deps

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

EXPOSE 10000

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000", "--workers", "1", "--timeout", "120"]
