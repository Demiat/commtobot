FROM python:3.12-alpine

WORKDIR /

COPY requirements.txt .

RUN pip install -r requirements.txt --no-cache-dir

COPY russian_trusted_root_ca.cer /tmp/russian_trusted_root_ca.cer

COPY install.sh .
RUN chmod +x install.sh && ./install.sh

COPY . .

CMD ["python", "bot.py"] 