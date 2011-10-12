#!/usr/bin/python
# network.py - Copyright (C) 2010 Red Hat, Inc.
# Written by Joey Boggs <jboggs@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.  A copy of the GNU General Public License is
# also available at http://www.gnu.org/copyleft/gpl.html.
from ovirtnode.ovirtfunctions import *
from glob import glob
import tempfile
import sys

class Network:

    def __init__(self):
        OVIRT_VARS = parse_defaults()
        self.WORKDIR=tempfile.mkdtemp()
        self.IFSCRIPTS_PATH ="/etc/sysconfig/network-scripts/ifcfg-"
        self.IFCONFIG_FILE_ROOT="/files%s" % self.IFSCRIPTS_PATH
        self.NTP_CONFIG_FILE="/etc/ntp.conf"
        self.NTPSERVERS=""
        self.CONFIGURED_NIC = ""
        self.CONFIGURED_NICS = []
        self.IF_CONFIG = ""
        self.BR_CONFIG = ""
        self.VL_CONFIG = ""
        self.VLAN_ID=""
        self.VL_ROOT=""
        self.VL_FILENAME =""
        self.nic=""
        self.bridge=""
        self.vlan_id=""

    def configure_interface(self):
        log("Configuring Interface")
        self.disabled_nic = 0
        if OVIRT_VARS.has_key("OVIRT_IP_ADDRESS"):
            IPADDR = OVIRT_VARS["OVIRT_IP_ADDRESS"]
            NETMASK = OVIRT_VARS["OVIRT_IP_NETMASK"]
            GATEWAY = OVIRT_VARS["OVIRT_IP_GATEWAY"]

        if self.CONFIGURED_NIC is None:
            log("\nAborting...\n")
            return False

        if OVIRT_VARS.has_key("OVIRT_BOOTIF"):
            if OVIRT_VARS["OVIRT_BOOTIF"].endswith("-DISABLED"):
                self.disabled_nic = 1
            self.CONFIGURED_NIC = OVIRT_VARS["OVIRT_BOOTIF"].strip("-DISABLED")

        n_address = open("/sys/class/net/" + self.CONFIGURED_NIC + "/address")
        nic_hwaddr = n_address.readline().strip("\n")
        n_address.close()
        BRIDGE = "br" + self.CONFIGURED_NIC
        self.CONFIGURED_NICS.append(self.CONFIGURED_NIC)
        self.CONFIGURED_NICS.append(BRIDGE)
        IF_FILENAME = self.WORKDIR + "/augtool-" + self.CONFIGURED_NIC
        BR_FILENAME = self.WORKDIR + "/augtool-" + BRIDGE
        log("\nConfigure $BRIDGE for use by $NIC..\n\n")
        IF_ROOT = "%s%s" % (self.IFCONFIG_FILE_ROOT, self.CONFIGURED_NIC)
        self.IF_CONFIG += "rm %s\nset %s/DEVICE %s\n" % (IF_ROOT, IF_ROOT, self.CONFIGURED_NIC)
        self.IF_CONFIG += "set %s/HWADDR %s\n" % (IF_ROOT, nic_hwaddr)
        BR_ROOT = "%s%s" % (self.IFCONFIG_FILE_ROOT, BRIDGE)
        self.BR_CONFIG += "rm %s\nset %s/DEVICE %s\n" % (BR_ROOT, BR_ROOT, BRIDGE)
        self.BR_CONFIG += "set %s/TYPE Bridge\n" % BR_ROOT
        self.BR_CONFIG += "set %s/PEERNTP yes\n" % BR_ROOT
        self.BR_CONFIG += "set %s/DELAY 0\n" % BR_ROOT
        if OVIRT_VARS.has_key("OVIRT_IPV6"):
            if OVIRT_VARS["OVIRT_IPV6"]  == "auto":
                self.BR_CONFIG += "set %s/IPV6INIT yes\n" % BR_ROOT
                self.BR_CONFIG += "set %s/IPV6FORWARDING no\n" % BR_ROOT
                self.BR_CONFIG += "set %s/IPV6_AUTOCONF yes\n" % BR_ROOT
            elif OVIRT_VARS["OVIRT_IPV6"] == "dhcp":
                self.BR_CONFIG += "set %s/IPV6INIT yes\n" % BR_ROOT
                self.BR_CONFIG += "set %s/IPV6_AUTOCONF no\n" % BR_ROOT
                self.BR_CONFIG += "set %s/IPV6FORWARDING no\n" % BR_ROOT
                self.BR_CONFIG += "set %s/DHCPV6C yes\n" % BR_ROOT
            elif OVIRT_VARS["OVIRT_IPV6"] == "static":
                self.BR_CONFIG += "set %s/IPV6INIT yes\n" % BR_ROOT
                self.BR_CONFIG += "set %s/IPV6ADDR %s/%s\n" % (BR_ROOT, OVIRT_VARS["OVIRT_IPV6_ADDRESS"], OVIRT_VARS["OVIRT_IPV6_NETMASK"])
                self.BR_CONFIG += "set %s/IPV6_AUTOCONF no\n" % BR_ROOT
                self.BR_CONFIG += "set %s/IPV6FORWARDING no\n" % BR_ROOT
                self.BR_CONFIG += "set %s/IPV6_DEFAULTGW %s\n" % (BR_ROOT, OVIRT_VARS["OVIRT_IPV6_GATEWAY"])
        else:
            self.BR_CONFIG += "set %s/IPV6INIT no\n" % BR_ROOT
            self.BR_CONFIG += "set %s/IPV6_AUTOCONF no\n" % BR_ROOT
            self.BR_CONFIG += "set %s/IPV6FORWARDING no\n" % BR_ROOT


        if OVIRT_VARS.has_key("OVIRT_VLAN"):
            VLAN_ID=OVIRT_VARS["OVIRT_VLAN"]
            self.CONFIGURED_NICS.append("%s.%s" % (self.CONFIGURED_NIC, VLAN_ID))
            VL_ROOT = "%s.%s" % (IF_ROOT, VLAN_ID)
            self.VL_CONFIG += "rm %s\n" % VL_ROOT
            self.VL_CONFIG += "set %s/DEVICE %s.%s\n" % (VL_ROOT, self.CONFIGURED_NIC, VLAN_ID)
            self.VL_CONFIG += "set %s/HWADDR %s\n" % (VL_ROOT, nic_hwaddr)
            self.VL_CONFIG += "set %s/BRIDGE %s\n" % (VL_ROOT, BRIDGE)
            self.VL_CONFIG += "set %s/VLAN yes\n" % VL_ROOT
            self.VL_FILENAME = "%s.%s" % (IF_FILENAME, OVIRT_VARS["OVIRT_VLAN"])
            self.VL_CONFIG +="set %s/ONBOOT yes" % VL_ROOT


        if not OVIRT_VARS.has_key("OVIRT_IP_ADDRESS"):
            if OVIRT_VARS.has_key("OVIRT_BOOTIF") and self.disabled_nic == 0:
                if not self.VL_CONFIG:
	            self.IF_CONFIG += "set %s/BRIDGE %s\n" % (IF_ROOT, BRIDGE)
                self.BR_CONFIG += "set %s/BOOTPROTO dhcp\n" % BR_ROOT
            elif self.disabled_nic == 1:
                self.BR_CONFIG += "set %s/BOOTPROTO none\n" % BR_ROOT

        elif OVIRT_VARS.has_key("OVIRT_IP_ADDRESS"):
            if OVIRT_VARS.has_key("OVIRT_IP_ADDRESS") and OVIRT_VARS["OVIRT_IP_ADDRESS"] != "off":
                self.BR_CONFIG += "set %s/BOOTPROTO static\n" % (BR_ROOT)
		if self.VL_CONFIG == "":
                    self.IF_CONFIG += "set %s/BRIDGE %s\n" % (IF_ROOT, BRIDGE)
                self.BR_CONFIG += "set %s/IPADDR %s\n" % (BR_ROOT, OVIRT_VARS["OVIRT_IP_ADDRESS"])
                if OVIRT_VARS.has_key("OVIRT_IP_NETMASK"):
                    self.BR_CONFIG += "set %s/NETMASK %s\n" % (BR_ROOT, OVIRT_VARS["OVIRT_IP_NETMASK"])
                if OVIRT_VARS.has_key("OVIRT_IP_GATEWAY"):
                    self.BR_CONFIG += "set %s/GATEWAY %s\n" % (BR_ROOT, OVIRT_VARS["OVIRT_IP_GATEWAY"])

        self.IF_CONFIG += "set %s/ONBOOT yes" % IF_ROOT
        self.BR_CONFIG += "set %s/ONBOOT yes" % BR_ROOT
        self.IF_CONFIG = self.IF_CONFIG.split("\n")
        self.BR_CONFIG = self.BR_CONFIG.split("\n")
        try:
            self.VL_CONFIG = self_VL_CONFIG.split("\n")
        except:
            pass
        return True

    def configure_dns(self):
        if OVIRT_VARS.has_key("OVIRT_DNS"):
            DNS=OVIRT_VARS["OVIRT_DNS"]
            try:
                if not DNS is None:
                    DNS = DNS.split(",")
                    i = 1
                    for server in DNS:
                        setting = "/files/etc/resolv.conf/nameserver[%s]" % i
                        augtool("set", setting, server)
                        i = i + i
                    ovirt_store_config("/etc/resolv.conf")
            except:
                log("Failed to set DNS servers")
            finally:
                if len(DNS) < 2:
                    augtool("rm", "/files/etc/resolv.conf/nameserver[2]", "")

    def configure_ntp(self):
        if OVIRT_VARS.has_key("OVIRT_NTP"):
            NTPSERVERS=OVIRT_VARS["OVIRT_NTP"]
        else:
            NTPSERVERS=""

    def save_ntp_configuration(self):
        ntproot = "/files/etc/ntp.conf"
        ntpconf = "rm %s\n" % ntproot
        ntpconf += "set %s/driftfile /var/lib/ntp/drift\n" % ntproot
        ntpconf += "set %s/includefile /etc/ntp/crypto/pw\n" % ntproot
        ntpconf += "set %s/keys /etc/ntp/keys" % ntproot
        ntpconf = ntpconf.split("\n")
        for line in ntpconf:
            try:
                oper, key, value = line.split()
                augtool(oper, key, value)
            except:
                oper, key = line.split()
                augtool(oper, key, "")

        if OVIRT_VARS.has_key("OVIRT_NTP"):
            offset=1
            SERVERS = OVIRT_VARS["OVIRT_NTP"].split(",")
            for server in SERVERS:
                if offset == 1:
                    augtool("set", "/files/etc/ntp.conf/server[1]", server)
                elif offset == 2:
                    augtool("set", "/files/etc/ntp.conf/server[2]", server)
                offset = offset + 1
            os.system("service ntpd stop &> /dev/null")
            os.system("service ntpdate start &> /dev/null")
            os.system("service ntpd start &> /dev/null")

    def save_network_configuration(self):
        aug.load()
        net_configured=0
        augtool_workdir_list = "ls %s/augtool-* >/dev/null"
        log("Configuring network")
        system("ifdown br" + self.CONFIGURED_NIC)
        for vlan in os.listdir("/proc/net/vlan/"):
            # XXX wrong match e.g. eth10.1 with eth1
            if self.CONFIGURED_NIC in vlan:
                os.system("vconfig rem " + vlan + "&> /dev/null")
                ovirt_safe_delete_config(self.IFSCRIPTS_PATH + vlan)
                os.system("rm -rf " + self.IFSCRIPTS_PATH + vlan)

        for script in glob("%s%s*" % (self.IFSCRIPTS_PATH, self.CONFIGURED_NIC)):
            # XXX wrong match e.g. eth10 with eth1* (need * to cover VLANs)
            log("Removing Script: " + script)
            ovirt_safe_delete_config(script)
        augtool("rm", self.IFCONFIG_FILE_ROOT+"br"+self.CONFIGURED_NIC, "")

        for line in self.IF_CONFIG:
            log(line)
            try:
                oper, key, value = line.split()
                augtool(oper, key, value)
            except:
                oper, key = line.split()
                augtool(oper, key, "")

        for line in self.BR_CONFIG:
            log(line)
            try:
                oper, key, value = line.split()
                augtool(oper, key, value)
            except:
                try:
                    oper, key = line.split()
                    augtool(oper, key, "")
                except:
                    pass

        for line in self.VL_CONFIG.split("\n"):
            log(line)
            try:
                oper, key, value = line.split()
                augtool(oper, key, value)
            except:
                try:
                    oper, key = line.split()
                    augtool(oper, key, "")
                except:
                    pass

        # preserve current MAC mappings for *all physical* network interfaces
        for nicdev in glob('/sys/class/net/*/device'):
            nic=nicdev.split('/')[4]
            if nic != self.CONFIGURED_NIC:
                f=open('/sys/class/net/%s/address' % nic)
                mac=f.read().strip()
                f.close()
                if len(mac) > 0:
                    self.CONFIGURED_NICS.append(nic)
                    nicroot = "%s%s" % (self.IFCONFIG_FILE_ROOT, nic)
                    # XXX augtool does save every time!
                    augtool("set", "%s/DEVICE" % nicroot, nic)
                    augtool("set", "%s/HWADDR" % nicroot, mac)
                    augtool("set", "%s/ONBOOT" % nicroot, "no")

        net_configured=1
        for nic in self.CONFIGURED_NICS:
            ovirt_store_config("%s%s" % (self.IFSCRIPTS_PATH, nic) )
        ovirt_store_config(self.NTP_CONFIG_FILE)
        augtool("set", "/files/etc/sysconfig/network/NETWORKING", "yes")
        ovirt_store_config("/etc/sysconfig/network")
        log("Network configured successfully")
        if net_configured == 1:
            log("\nStopping Network services")
            os.system("service network stop &> /dev/null")
            os.system("service ntpd stop &> /dev/null")
            # XXX eth assumed in breth
            brctl_cmd = "brctl show|grep breth|awk '{print $1}'"
            brctl = subprocess.Popen(brctl_cmd, shell=True, stdout=PIPE, stderr=STDOUT)
            brctl_output = brctl.stdout.read()
            for i in brctl_output.split():
                if_down_cmd = "ifconfig %s down &> /dev/null" % i
                os.system(if_down_cmd)
                del_br_cmd = "brctl delbr %s &> /dev/null" % i
                os.system(del_br_cmd)
            log("\nStarting Network service")
            os.system("service network start &> /dev/null")
            os.system("service ntpdate start &> /dev/null")
            os.system("service ntpd start &> /dev/null")
            # rhbz#745541
            os.system("service rpcbind start &> /dev/null")
            os.system("service nfslock start &> /dev/null")
            os.system("service rpcidmapd start &> /dev/null")
            os.system("service rpcgssd start &> /dev/null")
            if OVIRT_VARS.has_key("NTP"):
                log("Testing NTP Configuration")
                test_ntp_configuration()


if __name__ == "__main__":
    try:
        if "AUTO" in sys.argv[1]:
            if OVIRT_VARS.has_key("OVIRT_INIT"):
                network = Network()
                network.configure_interface()
                network.configure_dns()
                network.configure_ntp()
                network.save_ntp_configuration()
                network.save_network_configuration()
            else:
                log("No network interface specified. Unable to configure networking.")
    except:
        log("Exiting..")
        sys.exit(0)
