FROM python:3.12-slim
WORKDIR /app
RUN mkdir -p /app/data && useradd -m -u 10001 appuser && chown -R appuser:appuser /app
COPY --chown=10001:10001 server.py domain.py start.py index.html app.js ui.js styles.css ui.css nl.js enterprise.js enterprise.css integrations.js ./
COPY --chown=10001:10001 services/ ./services/
COPY --chown=10001:10001 assets/ ./assets/
USER appuser
ENV PORT=8080 ROEFS_HOST=0.0.0.0 ROEFS_DB=/app/data/roefs.db PYTHONDONTWRITEBYTECODE=1
EXPOSE 8080
CMD ["python", "-u", "start.py"]
