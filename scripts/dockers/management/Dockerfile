FROM phusion/baseimage:latest

RUN rm -f /etc/service/sshd/down
RUN /etc/my_init.d/00_regen_ssh_host_keys.sh
COPY init-ssh.py /var/run/
RUN mkdir -p /opt/code/github/0-complexity/openvcloud_installer/
RUN mkdir -p /opt/code/github/0-complexity/openvcloud/

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y sudo ipmitool curl python3 vim git sshpass gcc python3-dev tmux

RUN git clone https://github.com/rudecs/openvcloud.git /opt/code/github/0-complexity/openvcloud
RUN git clone https://github.com/rudecs/openvcloud_installer.git /opt/code/github/0-complexity/openvcloud_installer

RUN curl https://bootstrap.pypa.io/get-pip.py | python3
RUN pip3 install -r /opt/code/github/0-complexity/openvcloud_installer/requirements.txt

RUN mkdir -p /opt/cfg/system
