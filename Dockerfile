FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY docker-entrypoint.py /usr/local/bin/docker-entrypoint.py

RUN useradd -m appuser

ENTRYPOINT ["python", "/usr/local/bin/docker-entrypoint.py"]
CMD ["python", "-m", "src.pipeline"]