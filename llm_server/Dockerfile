FROM python:3.10-slim
WORKDIR /app
COPY ../requirements.txt /app/requirements.txt
RUN apt-get update && apt-get install -y build-essential libcurl4-openssl-dev git && rm -rf /var/lib/apt/lists/*
RUN pip install -r /app/requirements.txt
COPY . /app
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","5001"]
