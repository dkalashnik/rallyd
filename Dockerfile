FROM rallyforge/rally
MAINTAINER Dmitry Kalashnik <dkalashnik@mirantis.com>
USER root
RUN git clone https://github.com/dkalashnik/rallyd && \
    pip install ./rallyd/
USER rally
EXPOSE 8001
CMD rallyd --config-file /etc/rally/rally.conf
