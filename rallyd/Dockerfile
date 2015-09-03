FROM rallyforge/rally
MAINTAINER Dmitry Kalashnik <dkalashnik@mirantis.com>                      && \
           Sergey Novikov <snovikov@mirantis.com>
USER root

# Installation of rallyd and tempest cache

RUN git clone https://github.com/dkalashnik/rallyd                         && \
    pip install ./rallyd/rallyd/                                           && \
    apt-get -y install build-essential gcc-4.8 libffi-dev libssl-dev          \
                       libxml2-dev libxslt1-dev python-dev python          && \
    mkdir /opt/rallyd                                                      && \

    git clone https://github.com/openstack/tempest /opt/rallyd/tempest     && \
    pip install -r /opt/rallyd/tempest/requirements.txt                    && \

    chmod +w /etc/sudoers                                                  && \
    echo "rally ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers                   && \
    chmod -w /etc/sudoers

# Cleanup stuff from container

RUN apt-get -y remove build-essential gcc-4.8 libffi-dev libssl-dev           \
                      libxml2-dev libxslt1-dev python-dev                  && \
    apt-get -y autoremove && apt-get clean                                 && \
    rm -rf rallyd                                                          && \
    rm /home/rally/.rally.sqlite
USER rally

# (NOTE): Workaround for wrong db file rights
RUN rally-manage db recreate

EXPOSE 8000

CMD ["rallyd"]
