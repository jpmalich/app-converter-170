FROM python:3.11-slim-bookworm

# System libraries:
#  - WeasyPrint PDF rendering needs Pango / Cairo / GDK-PixBuf native libs
#  - build-essential + libffi-dev cover any source builds in requirements.txt
#  - shared-mime-info + fonts-liberation give WeasyPrint working MIME + fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libpangoft2-1.0-0 \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libjpeg62-turbo \
        libxml2 \
        libxslt1.1 \
        shared-mime-info \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# emergentintegrations (used by the AI routes) is published on Emergent's
# private index, not PyPI — pull it in via an extra index URL.
COPY requirements.txt .
RUN pip install --no-cache-dir \
        --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/ \
        -r requirements.txt

COPY . .

EXPOSE 8000

# --reload works because ./backend is bind-mounted in docker-compose.yml;
# watchfiles (in requirements.txt) drives the reloader.
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
