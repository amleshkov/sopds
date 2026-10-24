FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p opds_catalog/tmp opds_catalog/log

EXPOSE 8001

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["server"]
