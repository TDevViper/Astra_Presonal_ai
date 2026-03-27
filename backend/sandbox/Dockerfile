FROM python:3.11-slim
RUN useradd -m -u 1000 sandbox
RUN pip install --no-cache-dir numpy pandas matplotlib scipy requests 2>/dev/null || true
WORKDIR /code
USER sandbox
CMD ["python3", "-u", "/code/script.py"]
