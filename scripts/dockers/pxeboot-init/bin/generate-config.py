import yaml
import os
import subprocess

configroot = "/opt/pxeboot/conf"
tftproot = "/opt/pxeboot/tftpboot"
imageroot = "/opt/pxeboot/images"

with open("/etc/global/system-config.yaml", "r") as f:
    configfile = f.read()

config = yaml.load(configfile)
domain = config["environment"]["subdomain"]

netmask = "24"  # default to /24

if "/" not in config["network"]["management"]["network"]:
    print(
        "[-] WARNING: no cidr netmask specified on management network, fallback to /%s"
        % netmask
    )

else:
    netmask = config["network"]["management"]["network"].split("/")[1]

gateway = config["network"]["management"]["gateway"]
gatewaycidr = "%s/%s" % (gateway, netmask)
mgmtsubnet = config["network"]["management"]["network"].split("/")[0]
ipmisubnet = config["network"]["ipmi"]["network"].split("/")[0]

"""
dhcphosts file
"""
target = os.path.join(configroot, "dhcphosts")

with open(target, "w") as f:
    nodes = config["nodes"]
    roles = {"cpu", "storage", "controller"}
    for node in nodes:
        if roles.intersection(set(node["roles"])):
            if "macaddress" in node["management"]:
                f.write(
                    "%s,%s,infinite\n"
                    % (node["management"]["macaddress"].lower(), node["name"])
                )
            if "macaddress" in node["ipmi"]:
                f.write(
                    "%s,%s,infinite\n"
                    % (node["ipmi"]["macaddress"].lower(), "ipmi-%s" % node["name"])
                )

    f.write("\n")

"""
hosts file
"""
target = os.path.join(configroot, "hosts")

with open(target, "w") as f:
    nodes = config["nodes"]
    nodenet = mgmtsubnet.split(".")
    roles = {"cpu", "storage"}
    ipminet = ipmisubnet.split(".")
    for node in nodes:
        if roles.intersection(set(node["roles"])):
            ipaddr = "%s.%s.%s.%s" % (
                nodenet[0],
                nodenet[1],
                nodenet[2],
                node["ip-lsb"],
            )
            f.write("%s %s.%s %s\n" % (ipaddr, node["name"], domain, node["name"]))
            ipaddr = "%s.%s.%s.%s" % (
                ipminet[0],
                ipminet[1],
                ipminet[2],
                node["ip-lsb"],
            )
            f.write(
                "%s %s.%s %s\n"
                % (ipaddr, "ipmi-%s" % node["name"], domain, "ipmi-%s" % node["name"])
            )
        elif "controller" in node["roles"]:
            ipaddr = "%s.%s.%s.%s" % (
                ipminet[0],
                ipminet[1],
                ipminet[2],
                255 - node["ip-lsb"],
            )
            f.write(
                "%s %s.%s %s\n"
                % (ipaddr, "ipmi-%s" % node["name"], domain, "ipmi-%s" % node["name"])
            )

    f.write("\n")

"""
dnsmasq and pxelinux
"""
netconfig = {
    "%domain%": domain,
    "%range-lan%": mgmtsubnet,
    "%range-ipmi%": ipmisubnet,
    "%gateway%": gateway,
    "%option6%": gateway,
}

pxelinux = os.path.join(configroot, "tftp-911boot")
dnsmasq = os.path.join(configroot, "dnsmasq.conf")

for target in [pxelinux, dnsmasq]:
    with open(target, "r") as f:
        source = f.read()

    for entry in netconfig:
        source = source.replace(entry, netconfig[entry])

    with open(target, "w") as f:
        f.write(source)

"""
floating gateway ip
"""
gatewayfile = os.path.join(configroot, "gateway-ip-address")

with open(gatewayfile, "w") as f:
    f.write(gatewaycidr)
