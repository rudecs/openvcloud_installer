FROM openvcloud/cb_master

RUN mkdir -p /var/run/scripts/nginx/ /opt/cfg/nginx/ssl /opt/cfg/upgrade
COPY configure-nginx.py /var/run/scripts/nginx/
COPY nginx.conf /opt/cfg/nginx/templates/nginx.conf
COPY upgrade.conf /opt/cfg/nginx/templates/upgrade.conf
CMD mkdir -p /opt/code/github/openvcloud_installer/
CMD git clone https://github.com/rudecs/openvcloud_installer /opt/code/github/openvcloud_installer/
