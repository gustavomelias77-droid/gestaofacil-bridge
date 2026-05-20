FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir flask playwright
RUN playwright install --with-deps chromium
COPY app.py requirements.txt ./
EXPOSE 10000
CMD ["python", "app.py"]
