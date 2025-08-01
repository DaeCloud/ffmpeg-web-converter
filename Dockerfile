
FROM python:3.11-slim

RUN apt-get update && apt-get install -y ffmpeg cron && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Add cron job to clean files older than 24 hours
RUN echo "0 * * * * find /app/uploads -type f -mmin +1440 -delete && find /app/outputs -type f -mmin +1440 -delete" > /etc/cron.d/cleanup && \
    chmod 0644 /etc/cron.d/cleanup && \
    crontab /etc/cron.d/cleanup

RUN touch /var/log/cron.log

CMD cron && python app.py
