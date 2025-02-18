FROM alpine:latest
COPY ./requirements.txt /requirements.txt
RUN apk update --no-cache && apk upgrade --no-cache \
&& apk add --no-cache python3 \
&& apk add --no-cache --virtual .build-dependencies py-pip \
&& pip install --no-cache-dir --break-system-packages -r /requirements.txt \
&& apk del .build-dependencies \
&& rm /requirements.txt
COPY ./app /app
WORKDIR /app
ENTRYPOINT [ "/usr/bin/python3", "/app/run.py" ]