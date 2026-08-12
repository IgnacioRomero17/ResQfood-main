FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt && \
    pip install gunicorn whitenoise

COPY . /app/

RUN mkdir -p /app/staticfiles /app/media

CMD ["sh", "-c", "\
python manage.py collectstatic --noinput && \
python manage.py migrate && \
gunicorn resqfood.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120 \
"]
