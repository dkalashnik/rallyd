#!/bin/bash

COUNT=1
for ip in ${BACKEND_IPS}
do
    sudo sed -i "\$aserver backend${COUNT} ${ip} check" /etc/haproxy/haproxy.cfg 
    COUNT=$((${COUNT} + 1))
done

sudo /etc/init.d/haproxy restart

rallyd --config-file /etc/rally/rally.conf
