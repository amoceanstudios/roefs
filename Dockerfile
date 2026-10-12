FROM python:3.12-slim
WORKDIR /app
RUN mkdir -p /app/data && useradd -m -u 10001 appuser && chown -R appuser:appuser /app
COPY --chown=10001:10001 server.py domain.py start.py manage.py requirements-security.txt index.html app.js ui.js styles.css ui.css nl.js enterprise.js enterprise.css integrations.js events.js ./
COPY --chown=10001:10001 services/ ./services/
COPY --chown=10001:10001 assets/ ./assets/
ARG WITH_BACKUP_ENCRYPTION=0
RUN if [ "$WITH_BACKUP_ENCRYPTION" = "1" ]; then pip install --no-cache-dir -r requirements-security.txt; fi
USER appuser
ENV PORT=8080 ROEFS_HOST=0.0.0.0 ROEFS_DB=/app/data/roefs.db PYTHONDONTWRITEBYTECODE=1
EXPOSE 8080
CMD ["python", "-u", "start.py"]
