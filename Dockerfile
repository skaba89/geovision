FROM python:3.13-slim
WORKDIR /app
RUN useradd --system --uid 10001 --no-create-home web
COPY server.py /app/
COPY site /app/site
USER 10001:10001
EXPOSE 8080
CMD ["python","-u","server.py"]
