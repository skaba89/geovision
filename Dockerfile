FROM python:3.13-slim
WORKDIR /app
RUN useradd --system --uid 10001 --no-create-home web
COPY server.py /app/
COPY site /app/site
# Les sources peuvent provenir d'un checkout avec umask 077.
RUN chmod 0644 /app/server.py && find /app/site -type d -exec chmod 0755 {} + && find /app/site -type f -exec chmod 0644 {} +
USER 10001:10001
EXPOSE 8080
CMD ["python","-u","server.py"]
