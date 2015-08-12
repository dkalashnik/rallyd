FROM rallyforge/rally
MAINTAINER Dmitry Kalashnik <dkalashnik@mirantis.com>                        && \
           Sergey Novikov <snovikov@mirantis.com>
USER root
RUN  echo deb http://archive.ubuntu.com/ubuntu trusty-backports main universe | \
     tee /etc/apt/sources.list.d/backports.list                              && \
     apt-get update && apt-get install -y haproxy -t trusty-backports
RUN git clone https://github.com/dkalashnik/rallyd                           && \
    pip install ./rallyd/
RUN cp /rallyd/haproxy.cfg.sample /etc/haproxy/haproxy.cfg
RUN chmod +w /etc/sudoers                                                    && \
    echo "rally ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers                     && \
    chmod -w /etc/sudoers
USER rally
EXPOSE 8001
CMD ["/bin/bash", "-c", "/rallyd/start.sh"]
