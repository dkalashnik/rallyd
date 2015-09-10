FROM rallyforge/rally
MAINTAINER Dmitry Kalashnik <dkalashnik@mirantis.com>                      && \
           Sergey Novikov <snovikov@mirantis.com>
USER root

COPY . /tmp/rallyd

RUN pip install /tmp/rallyd/ &&  rm -rf /tmp/rallyd                        && \

    # (NOTE): Workaround for wrong db file rights
    rm /home/rally/.rally.sqlite && rally-manage db recreate

EXPOSE 8000

CMD ["rallyd"]
