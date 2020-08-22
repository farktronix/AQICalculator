FROM python:3.6.12-alpine3.12
MAINTAINER farktronix

RUN pip3 install influxdb

COPY crontab /etc/crontabs/root

COPY aqicalc.py /root/
RUN chmod +x /root/aqicalc.py

ENTRYPOINT ["crond", "-f", "-d", "8"]
