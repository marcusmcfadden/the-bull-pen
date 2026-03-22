FROM python:3.11-slim

WORKDIR /app

COPY App/bullpen/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY App/bullpen/ ./bullpen
COPY App/assets/ ./assets

WORKDIR /app/bullpen

EXPOSE 8080

CMD ["python", "main.py"]