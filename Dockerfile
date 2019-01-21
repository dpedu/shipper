FROM ubuntu:bionic

RUN apt-get update && \
    apt-get install -y python3-pip rsync openssh-client curl wget git && \
    rm -rf /var/lib/apt/lists/* && \
    useradd app

ADD . /tmp/code

RUN cd /tmp/code && \
    pip3 install -r requirements.txt

RUN cd /tmp/code && \
    python3 setup.py install

EXPOSE 8080
VOLUME /scripts
USER app
ENTRYPOINT ["shipperd", "-p", "8080", "-t", "/scripts"]
