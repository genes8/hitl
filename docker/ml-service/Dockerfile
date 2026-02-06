FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir -U pip \
  && pip install --no-cache-dir fastapi==0.109.* uvicorn[standard]==0.27.*
CMD ["python", "-c", "print('ml-service placeholder')"]
