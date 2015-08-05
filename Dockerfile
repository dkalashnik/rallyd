FROM rallyforge/rally
MAINTAINER Dmitry Kalashnik <dkalashnik@mirantis.com>
USER root
RUN git clone https://github.com/dkalashnik/rallyd && \
    cd rallyd && python setup.py install
USER rally
EXPOSE 8001
CMD rallyd --config-file /etc/rally/rally.conf
