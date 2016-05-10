# 
# Copyright 2016-present Ciena Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from scapy.all import *

conf.verb = 0 # Disable Scapy verbosity
conf.checkIPaddr = 0 # Don't check response packets for matching destination IPs

class DHCPTest:

    def __init__(self, seed_ip = '192.168.1.1', iface = 'veth0'):
        self.seed_ip = seed_ip
        self.seed_mac = self.ipToMac(self.seed_ip)
        self.iface = iface
        self.mac_map = {}
        self.mac_inverse_map = {}
	self.bootpmac = None
	self.dhcpresp = None

    def is_mcast(self, ip):
        mcast_octet = (atol(ip) >> 24) & 0xff
        return True if mcast_octet >= 224 and mcast_octet <= 239 else False

    def discover(self, mac = None, update_seed = False):
        '''Send a DHCP discover/offer'''

        if mac is None:
            mac = self.seed_mac
            if update_seed:
                self.seed_ip = self.incIP(self.seed_ip)
                self.seed_mac = self.ipToMac(self.seed_ip)
                mac = self.seed_mac

        chmac = self.macToChaddr(mac)
	self.bootpmac = chmac
        L2 = Ether(dst="ff:ff:ff:ff:ff:ff", src=mac)
        L3 = IP(src="0.0.0.0", dst="255.255.255.255")
        L4 = UDP(sport=68, dport=67)
        L5 = BOOTP(chaddr=chmac)
        L6 = DHCP(options=[("message-type","discover"),"end"])
        resp = srp1(L2/L3/L4/L5/L6, filter="udp and port 68", timeout=10, iface=self.iface)
	self.dhcpresp = resp
        try:
            srcIP = resp.yiaddr
            serverIP = resp.siaddr
        except AttributeError:
            print("Failed to acquire IP via DHCP for %s on interface %s" %(mac, self.iface))
            return (None, None)

        subnet_mask = "0.0.0.0"
        for x in resp.lastlayer().options:
            if(x == 'end'):
                break
            op,val = x
            if(op == "subnet_mask"):
                subnet_mask = val
            elif(op == 'server_id'):
                server_id = val

        L5 = BOOTP(chaddr=chmac, yiaddr=srcIP)
        L6 = DHCP(options=[("message-type","request"), ("server_id",server_id),
                           ("subnet_mask",subnet_mask), ("requested_addr",srcIP), "end"])
        srp(L2/L3/L4/L5/L6, filter="udp and port 68", timeout=10, iface=self.iface)
        self.mac_map[mac] = (srcIP, serverIP)
        self.mac_inverse_map[srcIP] = (mac, serverIP)
        return (srcIP, serverIP)

    def only_discover(self, mac = None, desired = False, lease_time = False):  
        '''Send a DHCP discover'''

        if mac is None:
            mac = self.seed_mac

        chmac = self.macToChaddr(mac)
	self.bootpmac = chmac
        L2 = Ether(dst="ff:ff:ff:ff:ff:ff", src=mac)
        L3 = IP(src="0.0.0.0", dst="255.255.255.255")
        L4 = UDP(sport=68, dport=67)
        L5 = BOOTP(chaddr=chmac)
	if desired:
		L6 = DHCP(options=[("message-type","discover"),("requested_addr",self.seed_ip),"end"])
	
	elif time:
		L6 = DHCP(options=[("message-type","discover"),("lease_time",700),"end"])
		
	elif lease_time:
        	L6 = DHCP(options=[("message-type","discover"),"end"])

		

        resp = srp1(L2/L3/L4/L5/L6, filter="udp and port 68", timeout=10, iface=self.iface)
	if resp == None:
        	return (None, None, None)
		
	self.dhcpresp = resp
        for x in resp.lastlayer().options:
            if(x == 'end'):
                break
            op,val = x
            if(op == "message-type"):
            	
	    	if(val == 2):
		
			try:
            			srcIP = resp.yiaddr
            			serverIP = resp.siaddr
        		except AttributeError:
           			print "In Attribute error."
            		 	print("Failed to acquire IP via DHCP for %s on interface %s" %(mac, self.iface))
            		 	return (None, None, None)
			
			if lease_time == True:
				for x in resp.lastlayer().options:
            				if(x == 'end'):
                				break
            				op,val = x
            				if(op == "lease_time"):
						return (srcIP, serverIP, mac, val)
			else:
				return (srcIP, serverIP, mac)
	
		elif(val == 6):
		
			return (None, None, mac)

	
    def only_request(self, cip, mac):
        '''Send a DHCP offer'''
        
	subnet_mask = "0.0.0.0"
        for x in self.dhcpresp.lastlayer().options:
            	if(x == 'end'):
                	break
            	op,val = x
            	if(op == "subnet_mask"):
                	subnet_mask = val
            	elif(op == 'server_id'):
                	server_id = val

        L2 = Ether(dst="ff:ff:ff:ff:ff:ff", src=mac)
        L3 = IP(src="0.0.0.0", dst="255.255.255.255")
        L4 = UDP(sport=68, dport=67)
        L5 = BOOTP(chaddr=self.bootpmac, yiaddr=cip)
        L6 = DHCP(options=[("message-type","request"), ("server_id",server_id),
                           ("subnet_mask",subnet_mask), ("requested_addr",cip), "end"])
	resp=srp1(L2/L3/L4/L5/L6, filter="udp and port 68", timeout=10, iface=self.iface)
	if resp == None:
        	return (None, None)
        
	for x in resp.lastlayer().options:
            	if(x == 'end'):
                	break
            	op,val = x
            	if(op == "message-type"):
	
			if(val == 5):
        	
				try:
            				srcIP = resp.yiaddr
            				serverIP = resp.siaddr
        			except AttributeError:
           				print "In Attribute error."
            				print("Failed to acquire IP via DHCP for %s on interface %s" %(mac, self.iface))
            				return (None, None)
	        		self.mac_map[mac] = (srcIP, serverIP)
        			self.mac_inverse_map[srcIP] = (mac, serverIP)

				return (srcIP, serverIP)
	
			elif(val == 6):
		
				return (None, None)
	
		

    def discover_next(self):
        '''Send next dhcp discover/request with updated mac'''
        return self.discover(update_seed = True)

    def release(self, ip):
        '''Send a DHCP discover/offer'''
        if ip is None:
            return False
        if not self.mac_inverse_map.has_key(ip):
            return False
        mac, server_ip = self.mac_inverse_map[ip]
        chmac = self.macToChaddr(mac)
        L2 = Ether(dst="ff:ff:ff:ff:ff:ff", src=mac)
        L3 = IP(src="0.0.0.0", dst="255.255.255.255")
        L4 = UDP(sport=68, dport=67)
        L5 = BOOTP(chaddr=chmac, ciaddr = ip)
        L6 = DHCP(options=[("message-type","release"), ("server_id", server_ip), "end"])
        sendp(L2/L3/L4/L5/L6, iface = self.iface)
        del self.mac_map[mac]
        del self.mac_inverse_map[ip]
        return True

    def macToChaddr(self, mac):
        rv = []
        mac = mac.split(":")
        for x in mac:
            rv.append(chr(int(x, 16)))
        return reduce(lambda x,y: x + y, rv)

    def get_ip(self, mac):
        if self.mac_map.has_key(mac):
            return self.mac_map[mac]
        return (None, None)

    def get_mac(self, ip):
        if self.mac_inverse_map.has_key(ip):
            return self.mac_inverse_map[ip]
        return (None, None)

    def ipToMac(self, ip):
        '''Generate a mac from a ip'''

        mcast = self.is_mcast(ip)
        mac = "01:00:5e" if mcast == True else "00:00:00"
        octets = ip.split(".")
        for x in range(1,4):
            num = str(hex(int(octets[x])))
            num =  num.split("x")[1]
            if len(num) < 2:
                num = "0" + str(num)
            mac += ":" + num
        return mac

    def incIP(self, ip, n=1):
        '''Increment an IP'''

        if n < 1:
            return ip
        o = ip.split(".")
        for ii in range(3,-1,-1):
            if int(o[ii]) < 255:
                o[ii] = str(int(o[ii]) + 1)
                break
            else:
                o[ii] = str(0)

        n -= 1
        return self.incIP(".".join(o), n)
