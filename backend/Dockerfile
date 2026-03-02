FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Chromium + its system deps for Playwright (LinkedIn scraper)
# Note: in Docker this runs headless-only; LinkedIn scraping needs a local run
RUN playwright install --with-deps chromium

COPY . .

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
