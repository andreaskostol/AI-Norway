FROM python:3.12-slim
WORKDIR /app
COPY server.py /app/server.py
ENV PORT=8080 KIINDEKSEN_BASE=https://kiindeksen.no KIINDEKSEN_REFRESH_HOURS=6
EXPOSE 8080
CMD ["python3", "-u", "/app/server.py"]
