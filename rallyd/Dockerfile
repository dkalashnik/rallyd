FROM rallyforge/rally
MAINTAINER Dmitry Kalashnik <dkalashnik@mirantis.com>                      && \
           Sergey Novikov <snovikov@mirantis.com>
USER root

# Installation of rallyd and tempest cache
COPY . /tmp/rallyd
RUN pip install /tmp/rallyd/ && apt-get update                             && \
    apt-get -y install build-essential gcc-4.8 libffi-dev libssl-dev          \
                       libxml2-dev libxslt1-dev python-dev python          && \
    mkdir /opt/rallyd                                                      && \

    git clone https://github.com/openstack/tempest /opt/rallyd/tempest     && \
    pip install -r /opt/rallyd/tempest/requirements.txt                       \
                -r /opt/rallyd/tempest/test-requirements.txt               && \
    cd /opt/rallyd/tempest                                                 && \
    git config --global user.name "Dmitry Kalashnik"                       && \
    git config --global user.email "dkalashnik@mirantis.com"               && \
    git am /tmp/rallyd/0001-Enable-global-packages.patch                   && \
    chmod +w /etc/sudoers                                                  && \
    echo "rally ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers                   && \
    chmod -w /etc/sudoers

# Cleanup stuff from container

RUN apt-get -y remove build-essential gcc-4.8 libffi-dev libssl-dev           \
                      libxml2-dev libxslt1-dev python-dev                  && \
    apt-get -y autoremove && apt-get clean                                 && \
    rm -rf /tmp/rallyd                                                     && \
    rm /home/rally/.rally.sqlite
USER rally

# (NOTE): Workaround for wrong db file rights
RUN rally-manage db recreate

EXPOSE 8000

CMD ["rallyd"]
