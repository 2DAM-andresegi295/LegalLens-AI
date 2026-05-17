FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["sh", "-c", "python apps/web/manage.py migrate && python apps/web/manage.py collectstatic --noinput && gunicorn apps.web.config.wsgi:application --bind 0.0.0.0:8000"]

