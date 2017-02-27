#copyright 2016-present Ciena Corporation
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
import unittest
from nose.tools import *
from scapy.all import *
from OnosCtrl import OnosCtrl, get_mac
from OltConfig import OltConfig
from socket import socket
from OnosFlowCtrl import OnosFlowCtrl
from nose.twistedtools import reactor, deferred
from twisted.internet import defer
from onosclidriver import OnosCliDriver
from CordContainer import Container, Onos, Quagga
from CordTestServer import cord_test_onos_restart, cord_test_onos_shutdown
from portmaps import g_subscriber_port_map
from scapy.all import *
import time, monotonic
from OnosLog import OnosLog
from CordLogger import CordLogger
from os import environ as env
import os
import json
import random
import collections
import paramiko
from paramiko import SSHClient
log.setLevel('INFO')

class vsg_exchange(CordLogger):
    ONOS_INSTANCES = 3
    V_INF1 = 'veth0'
    device_id = 'of:' + get_mac()
    testcaseLoggers = ("")
    TEST_IP = '8.8.8.8'
    HOST = "10.1.0.1"
    USER = "vagrant"
    PASS = "vagrant"


    def setUp(self):
        if self._testMethodName not in self.testcaseLoggers:
            super(vsg_exchange, self).setUp()

    def tearDown(self):
        if self._testMethodName not in self.testcaseLoggers:
            super(vsg_exchange, self).tearDown()

    def get_controller(self):
        controller = os.getenv('ONOS_CONTROLLER_IP') or 'localhost'
        controller = controller.split(',')[0]
        return controller

    @classmethod
    def get_controllers(cls):
        controllers = os.getenv('ONOS_CONTROLLER_IP') or ''
        return controllers.split(',')

    def cliEnter(self, controller = None):
        retries = 0
        while retries < 30:
            self.cli = OnosCliDriver(controller = controller, connect = True)
            if self.cli.handle:
                break
            else:
                retries += 1
                time.sleep(2)

    def cliExit(self):
        self.cli.disconnect()

    def onos_shutdown(self, controller = None):
        status = True
        self.cliEnter(controller = controller)
        try:
            self.cli.shutdown(timeout = 10)
        except:
            log.info('Graceful shutdown of ONOS failed for controller: %s' %controller)
            status = False

        self.cliExit()
        return status

    def log_set(self, level = None, app = 'org.onosproject', controllers = None):
        CordLogger.logSet(level = level, app = app, controllers = controllers, forced = True)

    def get_nova_credentials_v2():
        credential = {}
        credential['version'] = '2'
        credential['username'] = env['OS_USERNAME']
        credential['api_key'] = env['OS_PASSWORD']
        credential['auth_url'] = env['OS_AUTH_URL']
        credential['project_id'] = env['OS_TENANT_NAME']
        return credential

    def get_vsg_ip(vm_id):
        credentials = get_nova_credentials_v2()
        nova_client = Client(**credentials)
        result = nova_client.servers.list()
        for server in result:
            print server;

    def health_check(self):
        cmd = "nova list --all-tenants|grep mysite_vsg|cut -d '|' -f 2"
        status, nova_id = commands.getstatusoutput(cmd)
        cmd = "nova interface-list {{ nova_id }}|grep -o -m 1 '172\.27\.[[:digit:]]*\.[[:digit:]]*'"
        status, ip = commands.getstatusoutput(cmd)
        cmd = "ping -c1 {0}".format(ip)
        status =  os.system(cmd)
        return status

    def ping_ip(remote, ip):
        results = []
        cmd = "ping -c1 {0}".format(ip)
        result = remote.execute(cmd, verbose=False)
        return results

    def vsg_vm_ssh_check(vsg_ip):
        cmd = "nc -z -v "+str(vsg_ip)+" 22"
        status =  os.system(cmd)
        return status

    def get_vcpe(self):
        cmd = "nova list --all-tenants|grep mysite_vsg|cut -d '|' -f 2"
        status, node_id = commands.getstatusoutput(cmd)

    def connect_ssh(vsg_ip, private_key_file=None, user='ubuntu'):
        key = ssh.RSAKey.from_private_key_file(private_key_file)
        client = ssh.SSHClient()
        client.set_missing_host_key_policy(ssh.WarningPolicy())
        client.connect(ip, username=user, pkey=key, timeout=5)
        return client

    def test_vsg_vm(self):
        status = self.health_check()
        assert_equal( status, False)

    def test_vsg_for_default_route_to_vsg_vm(self):
        client = SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect( self.HOST, username = self.USER, password=self.PASS)
        cmd = "sudo lxc exec testclient -- route | grep default"
        stdin, stdout, stderr = client.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        assert_equal( status, False)

    def test_vsg_vm_for_vcpe(self):
        client = SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect( self.HOST, username = self.USER, password=self.PASS)
        cmd = "nova service-list|grep nova-compute|cut -d '|' -f 3"
        stdin, stdout, stderr = client.exec_command(cmd)
        cmd = "nova list --all-tenants | grep mysite_vsg|cut -d '|' -f 7 | cut -d '=' -f 2 | cut -d ';' -f 1"
        status, ip = commands.getstatusoutput(cmd)
        #cmd = "ssh -o ProxyCommand="ssh -W %h:%p -l ubuntu {0}" ubuntu@{1} "sudo docker ps|grep vcpe"".format(compute_node_name, ip)
        status = stdout.channel.recv_exit_status()
        assert_equal( status, False)

    def test_vsg_for_external_connectivity(self):
        client = SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect( self.HOST, username = self.USER, password=self.PASS)
        cmd = "lxc exec testclient -- ping -c 3 8.8.8.8"
        stdin, stdout, stderr = client.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        assert_equal( status, False)

    def test_vsg_cord_subscriber_creation(self):
        pass

    def test_vsg_for_dhcp_client(self):
        pass

    def test_vsg_for_snat(self):
        pass

    def test_vsg_for_ping_from_vsg_to_external_network(self):
	"""
	Algo:
	1.Create a vSG VM in compute node
	2.Ensure VM created properly
	3.Verify login to VM success
	4.Do ping to external network from vSG VM
	5.Verify that ping gets success
	6.Verify ping success flows added in OvS
	"""
    def test_vsg_for_ping_from_vcpe_to_external_network(self):
        """
        Algo:
        1.Create a vSG VM in compute node
        2.Create a vCPE container inside VM
	3.Verify both VM and Container created properly
        4.Verify login to vCPE container success
        5.Do ping to external network from vCPE container
        6.Verify that ping gets success
        7.Verify ping success flows added in OvS
        """

    def test_vsg_for_dns_service(self):
	"""
	Algo:
	1. Create a test client  in Prod VM
	2. Create a vCPE container in vSG VM inside compute Node
	3. Ensure vSG VM and vCPE container created properly
	4. Enable dns service in vCPE ( if not by default )
	5. Send ping request from test client to valid domain  address say, 'www.google'com
	6. Verify that dns should resolve ping should success
	7. Now  send ping request to invalid domain address say 'www.invalidaddress'.com'
	8. Verify that dns resolve should fail and hence ping
        """
    def test_vsg_for_10_subscribers_for_same_service(self):
	"""
	Algo:
	1.Create a vSG VM in compute node
	2.Create 10 vCPE containers for 10 subscribers, in vSG VM
	3.Ensure vSG VM and vCPE container created properly
	4.From each of the subscriber, with same s-tag and different c-tag, send a ping to valid external public IP
	5.Verify that ping success for all 10 subscribers
	"""
    def test_vsg_for_10_subscribers_for_same_service_ping_invalid_ip(self):
        """
        Algo:
        1.Create a vSG VM in compute Node
	2.Create 10 vCPE containers for 10 subscribers, in vSG VM
	3.Ensure vSG VM and vCPE container created properly
        4.From each of the subscriber, with same s-tag and different c-tag, send a ping to invalid IP
        5.Verify that ping fails for all 10 subscribers
        """
    def test_vsg_for_10_subscribers_for_same_service_ping_valid_and_invalid_ip(self):
        """
        Algo:
        1.Create a vSG VM in VM
	2.Create 10 vCPE containers for 10 subscribers, in vSG VM
	3.Ensure vSG VM and vCPE container created properly
        4.From first 5 subscribers, with same s-tag and different c-tag, send a ping to valid IP
        5.Verify that ping success for all 5 subscribers
        6.From next 5 subscribers, with same s-tag and different c-tag, send a ping to invalid IP
        7.Verify that ping fails for all 5 subscribers
        """
    def test_vsg_for_100_subscribers_for_same_service(self):
	"""
	Algo:
	1.Create a vSG VM in compute node
	2.Create 100 vCPE containers for 100 subscribers, in vSG VM
	3.Ensure vSG VM and vCPE container created properly
	4.From each of the subscriber, with same s-tag and different c-tag, send a ping to valid external public IP
	5.Verify that ping success for all 100 subscribers
	"""
    def test_vsg_for_100_subscribers_for_same_service_ping_invalid_ip(self):
        """
        Algo:
        1.Create a vSG VM in compute Node
	2.Create 10 vCPE containers for 100 subscribers, in vSG VM
	3.Ensure vSG VM and vCPE container created properly
        4.From each of the subscriber, with same s-tag and different c-tag, send a ping to invalid IP
        5.Verify that ping fails for all 100 subscribers
        """
    def test_vsg_for_100_subscribers_for_same_service_ping_valid_and_invalid_ip(self):
        """
        Algo:
        1.Create a vSG VM in VM
	2.Create 10 vCPE containers for 100 subscribers, in vSG VM
	3.Ensure vSG VM and vCPE container created properly
        4.From first 5 subscribers, with same s-tag and different c-tag, send a ping to valid IP
        5.Verify that ping success for all 5 subscribers
        6.From next 5 subscribers, with same s-tag and different c-tag, send a ping to invalid IP
        7.Verify that ping fails for all 5 subscribers
        """
    def test_vsg_for_packet_received_with_invalid_ip_fields(self):
	"""
	Algo:
	1.Create a vSG VM in compute node
	2.Create a vCPE container in vSG VM
	3.Ensure vSG VM and vCPE container created properly
	4.From subscriber, send a ping packet with invalid ip fields
	5.Verify that vSG drops the packet
	6.Verify ping fails
	"""
    def test_vsg_for_packet_received_with_invalid_mac_fields(self):
        """
        Algo:
        1.Create a vSG VM in compute node
        2.Create a vCPE container in vSG VM
        3.Ensure vSG VM and vCPE container created properly
        4.From subscriber, send a ping packet with invalid mac fields
        5.Verify that vSG drops the packet
        6.Verify ping fails
        """
    def test_vsg_for_vlan_id_mismatch_in_stag(self):
        """
        Algo:
        1.Create a vSG VM in compute Node
	2.Create a vCPE container in vSG VM
	3.Ensure vSG VM and vCPE container created properly
        4.Send a ping request to external valid IP from subscriber, with incorrect vlan id in  s-tag and valid c-tag
        5.Verify that ping fails as the packet drops at VM entry
        6.Repeat step 4 with correct s-tag
	7.Verify that ping success
        """
    def test_vsg_for_vlan_id_mismatch_in_ctag(self):
        """
        Algo:
        1.Create a vSG VM in compute node
	2.Create a vCPE container in vSG VM
	3.Ensure vSG VM and vCPE container created properly
        4.Send a ping request to external valid IP from subscriber, with valid s-tag and incorrect vlan id in c-tag
        5.Verify that ping fails as the packet drops at vCPE container entry
        6.Repeat step 4 with valid s-tag and c-tag
        7.Verify that ping success
        """
    def test_vsg_for_matching_and_mismatching_vlan_id_in_stag(self):
        """
        Algo:
        1.Create two vSG VMs in compute node
	2.Create a vCPE container in each vSG VM
	3.Ensure vSG VM and vCPE container created properly
        4.From subscriber one, send ping request with valid s and c tags
        5.From subscriber two, send ping request with vlan id mismatch in s-tag and valid c tags
        6.Verify that ping success for only subscriber one and fails for two.
        """
    def test_vsg_for_matching_and_mismatching_vlan_id_in_ctag(self):
        """
        Algo:
        1.Create a vSG VM in compute node
	2.Create two vCPE containers in vSG VM
	3.Ensure vSG VM and vCPE container created properly
        4.From subscriber one, send ping request with valid s and c tags
        5.From subscriber two, send ping request with valid s-tag and vlan id mismatch in c-tag
        6.Verify that ping success for only subscriber one and fails for two
        """
    def test_vsg_for_out_of_range_vlanid_in_ctag(self):
        """
        Algo:
        1.Create a vSG VM in compute node
	2.Create a vCPE container in vSG VM
	3.Ensure vSG VM and vCPE container created properly
        4.From subscriber, send ping request with valid stag and vlan id in c-tag is an out of range value ( like 0,4097 )
        4.Verify that ping fails as the ping packets drops at vCPE container entry
        """
    def test_vsg_for_out_of_range_vlanid_in_stag(self):
        """
        Algo:
        1.Create a vSG VM in compute node
	2.Create a vCPE container in vSG VM
	3.Ensure vSG VM and vCPE container created properly
        2.From subscriber, send ping request with vlan id in s-tag is an out of range value ( like 0,4097 ), with valid c-tag
        4.Verify that ping fails as the ping packets drops at vSG VM entry
        """
    def test_vsg_without_creating_vcpe_instance(self):
	"""
	Algo:
	1.Create a vSG VM in compute Node
	2.Ensure vSG VM created properly
	3.Do not create vCPE container inside vSG VM
	4.From a subscriber, send ping to external valid IP
	5.Verify that ping fails as the ping packet drops at vSG VM entry itself.
	"""
    def test_vsg_for_remove_vcpe_instance(self):
	"""
        Algo:
        1.Create a vSG VM in compute node
        2.Create a vCPE container in vSG VM
        3.Ensure vSG VM and vCPE container created properly
        4.From subscriber, send ping request with valid s-tag and c-tag
        5.Verify that ping success
	6.Verify ping success flows in OvS switch in compute node
	7.Now remove the vCPE container in vSG VM
	8.Ensure that the container removed properly
	9.Repeat step 4
	10.Verify that now, ping fails
        """
    def test_vsg_for_restart_vcpe_instance(self):
        """
        Algo:
        1.Create a vSG VM in compute node
        2.Create a vCPE container in vSG VM
        3.Ensure vSG VM and vCPE container created properly
        4.From subscriber, send ping request with valid s-tag and c-tag
        5.Verify that ping success
        6.Verify ping success flows in OvS switch in compute node
        7.Now restart the vCPE container in vSG VM
        8.Ensure that the container came up after restart
        9.Repeat step 4
        10.Verify that now,ping gets success and flows added in OvS
        """
    def test_vsg_for_restart_vsg_vm(self):
        """
        Algo:
        1.Create a vSG VM in compute node
        2.Create a vCPE container in vSG VM
        3.Ensure vSG VM and vCPE container created properly
        4.From subscriber, send ping request with valid s-tag and c-tag
        5.Verify that ping success
        6.Verify ping success flows in OvS switch in compute node
        7.Now restart the vSG VM
        8.Ensure that the vSG comes up properly after restart
	9.Verify that vCPE container comes up after vSG restart
        10.Repeat step 4
        11.Verify that now,ping gets success and flows added in OvS
        """
    def test_vsg_for_pause_vcpe_instance(self):
        """
        Algo:
        1.Create a vSG VM in compute node
        2.Create a vCPE container in vSG VM
        3.Ensure vSG VM and vCPE container created properly
        4.From subscriber, send ping request with valid s-tag and c-tag
        5.Verify that ping success
        6.Verify ping success flows in OvS switch in compute node
        7.Now pause vCPE container in vSG VM for a while
        8.Ensure that the container state is pause
        9.Repeat step 4
        10.Verify that now,ping fails now and verify flows in OvS
	11.Now  resume the container
	12.Now repeat step 4 again
	13.Verify that now, ping gets success
	14.Verify ping success flows in OvS
        """
    def test_vsg_for_extract_all_compute_stats_from_all_vcpe_containers(self):
	"""
	Algo:
	1.Create a vSG VM in compute node
	2.Create 10 vCPE containers in VM
	3.Ensure vSG VM and vCPE containers created properly
	4.Login to all vCPE containers
	4.Get all compute stats from all vCPE containers
	5.Verify the stats # verification method need to add
	"""
    def test_vsg_for_extract_dns_stats_from_all_vcpe_containers(self):
        """
        Algo:
        1.Create a vSG VM in compute node
        2.Create 10 vCPE containers in VM
        3.Ensure vSG VM and vCPE containers created properly
	4.From  10 subscribers, send ping to valid and invalid dns hosts
        5.Verify dns resolves and ping success for valid dns hosts
	6.Verify ping fails for invalid dns hosts
        7.Verify dns host name resolve flows in OvS
	8.Login to all 10 vCPE containers
	9.Extract all dns stats
	10.Verify dns stats for queries sent, queries received for dns host resolve success and failed scenarios
        """
    def test_vsg_for_subscriber_access_two_vsg_services(self):
	"""
	# Intention is to verify if subscriber can reach internet via two vSG VMs
	Algo:
	1.Create two vSG VMs for two services in compute node
	2.Create one vCPE container in each VM for one subscriber
	3.Ensure VMs and containers created properly
	4.From subscriber end, send ping to public IP with stag corresponds to vSG-1 VM and ctag
	5.Verify ping gets success
	6.Verify ping success flows in OvS
	7.Now repeat step 4 with stag corresponds to vSG-2 VM
	8.Verify that ping again success
	9.Verify ping success flows in OvS
	"""
    def test_vsg_for_subscriber_access_service2_if_service1_goes_down(self):
	"""
	# Intention is to verify if subscriber can reach internet via vSG2 if vSG1 goes down
        Algo:
        1.Create two vSG VMs for two services in compute node
        2.Create one vCPE container in each VM for one subscriber
        3.Ensure VMs and containers created properly
        4.From subscriber end, send ping to public IP with stag corresponds to vSG-1 VM and ctag
        5.Verify ping gets success
        6.Verify ping success flows in OvS
	7.Down the vSG-1 VM
        8.Now repeat step 4
	9.Verify that ping fails as vSG-1 is down
        10.Repeat step 4 with stag corresponding to vSG-2
        9.Verify ping success and flows added in OvS
        """
    def test_vsg_for_subscriber_access_service2_if_service1_goes_restart(self):
        """
        # Intention is to verify if subscriber can reach internet via vSG2 if vSG1 restarts
        Algo:
        1.Create two vSG VMs for two services in compute node
        2.Create one vCPE container in each VM for one subscriber
        3.Ensure VMs and containers created properly
        4.From subscriber end, send ping to public IP with stag corresponds to vSG-1 VM and ctag
        5.Verify ping gets success
        6.Verify ping success flows added in OvS
        7.Now restart vSG-1 VM
        8.Now repeat step 4 while vSG-1 VM restarts
        9.Verify that ping fails as vSG-1 is restarting
        10.Repeat step 4 with stag corresponding to vSG-2 while vSG-1 VM restarts
        11.Verify ping success and flows added in OvS
        """
    def test_vsg_for_multiple_vcpes_in_vsg_vm_with_one_vcpe_goes_down(self):
        """
        # Intention is to verify if subscriber can reach internet via vSG2 if vSG1 goes down
        Algo:
        1.Create a vSG VM in compute node
        2.Create two vCPE containers corresponds to two subscribers in vSG VM
        3.Ensure VM and containers created properly
        4.From subscriber-1 end, send ping to public IP with ctag corresponds to vCPE-1 and stag
        5.Verify ping gets success
        6.Verify ping success flows added in OvS
        7.Now stop vCPE-1 container
        8.Now repeat step 4
        9.Verify that ping fails as vCPE-1 container is down
        10.Repeat step 4 with ctag corresponding to vCPE-2 container
        11.Verify ping success and flows added in OvS
        """
    def test_vsg_for_multiple_vcpes_in_vsg_vm_with_one_vcpe_restart(self):
        """
        # Intention is to verify if subscriber can reach internet via vSG2 if vSG1 restarts
        Algo:
        1.Create a vSG VM in compute node
        2.Create two vCPE containers corresponds to two subscribers in vSG VM
        3.Ensure VM and containers created properly
        4.From subscriber-1 end, send ping to public IP with ctag corresponds to vCPE-1 and stag
        5.Verify ping gets success
        6.Verify ping success flows added in OvS
        7.Now restart vCPE-1 container
        8.Now repeat step 4 while vCPE-1 restarts
        9.Verify that ping fails as vCPE-1 container is restarts
        10.Repeat step 4 with ctag corresponding to vCPE-2 container while vCPE-1 restarts
        11..Verify ping success and flows added in OvS
        """
    def test_vsg_for_multiple_vcpes_in_vsg_vm_with_one_vcpe_pause(self):
        """
        # Intention is to verify if subscriber can reach internet via vSG2 if vSG1 paused
        Algo:
        1.Create a vSG VM in compute node
        2.Create two vCPE containers corresponds to two subscribers in vSG VM
        3.Ensure VM and containers created properly
        4.From subscriber-1 end, send ping to public IP with ctag corresponds to vCPE-1 and stag
        5.Verify ping gets success
        6.Verify ping success flows added in OvS
        7.Now pause vCPE-1 container
        8.Now repeat step 4 while vCPE-1 in pause state
        9.Verify that ping fails as vCPE-1 container in pause state
        10.Repeat step 4 with ctag corresponding to vCPE-2 container while vCPE-1 in pause state
        11.Verify ping success and flows added in OvS
        """
    def test_vsg_for_multiple_vcpes_in_vsg_vm_with_one_vcpe_removed(self):
        """
        # Intention is to verify if subscriber can reach internet via vSG2 if vSG1 removed
        Algo:
        1.Create a vSG VM in compute node
        2.Create two vCPE containers corresponds to two subscribers in vSG VM
        3.Ensure VM and containers created properly
        4.From subscriber-1 end, send ping to public IP with ctag corresponds to vCPE-1 and stag
        5.Verify ping gets success
        6.Verify ping success flows added in OvS
        7.Now remove vCPE-1 container
        8.Now repeat step 4
        9.Verify that ping fails as vCPE-1 container removed
        10.Repeat step 4 with ctag corresponding to vCPE-2 container
        11.Verify ping success and flows added in OvS
        """
    def test_vsg_for_vcpe_instance_removed_and_added_again(self):
        """
        Algo:
        1.Create a vSG VM in compute node
        2.Create a vCPE container in vSG VM
        3.Ensure VM and containers created properly
        4.From subscriber end, send ping to public IP
        5.Verify ping gets success
        6.Verify ping success flows added in OvS
        7.Now remove vCPE container in vSG VM
        8.Now repeat step 4
        9.Verify that ping fails as vCPE container removed
	10.Create the vCPE container again for the same subscriber
	11.Ensure that vCPE created now
        12.Now repeat step 4
        13.Verify ping success and flows added in OvS
        """
    def test_vsg_for_vsg_vm_removed_and_added_again(self):
        """
        Algo:
        1.Create a vSG VM in compute node
        2.Create a vCPE container in vSG VM
        3.Ensure VM and containers created properly
        4.From subscriber end, send ping to public IP
        5.Verify ping gets success
        6.Verify ping success flows added in OvS
        7.Now remove vSG VM
        8.Now repeat step 4
        9.Verify that ping fails as vSG VM not exists
        10.Create the vSG VM and vCPE  container in VM again
        11.Ensure that vSG and vCPE created
        12.Now repeat step 4
        13.Verify ping success and flows added in OvS
        """

    #Test vSG - Subscriber Configuration
    def test_vsg_for_configuring_new_subscriber_in_vcpe(self):
	"""
	Algo:
	1.Create a vSG VM in compute node
        2.Create a vCPE container in vSG VM
        3.Ensure VM and containers created properly
	4.Configure a subscriber in XOS and assign a service id
	5.Set the admin privileges to the subscriber
	6.Verify subscriber configuration is success
	"""
    def test_vsg_for_adding_subscriber_devices_in_vcpe(self):
	"""
	Algo:
	1.Create a vSG VM in compute node
        2.Create a vCPE container in vSG VM
        3.Ensure VM and containers created properly
        4.Configure a subscriber in XOS and assign a service id
	5.Verify subscriber successfully configured in vCPE
	6.Now add devices( Mac addresses ) under the subscriber admin group
	7.Verify all devices ( Macs ) added successfully
	"""
    def test_vsg_for_removing_subscriber_devices_in_vcpe(self):
        """
        Algo:
        1.Create a vSG VM in compute node
        2.Create a vCPE container in vSG VM
        3.Ensure VM and containers created properly
        4.Configure a subscriber in XOS and assign a service id
        5.Verify subscriber successfully configured
        6.Now add devices( Mac addresses ) under the subscriber admin group
        7.Verify all devices ( Macs ) added successfully
	8.Now remove All the added devices in XOS
	9.Verify all the devices removed
        """
    def test_vsg_for_modify_subscriber_devices_in_vcpe(self):
        """
        Algo:
        1.Create a vSG VM in compute node
        2.Create a vCPE container in vSG VM
        3.Ensure VM and containers created properly
        4.Configure a user in XOS and assign a service id
        5.Verify subscriber successfully configured in vCPE.
        6.Now add devices( Mac addresses ) under the subscriber admin group
        7.Verify all devices ( Macs ) added successfully
        8.Now remove few devices in XOS
        9.Verify devices removed successfully
	10.Now add few additional devices in XOS  under the same subscriber admin group
	11.Verify newly added devices successfully added
        """
    def test_vsg_for_vcpe_login_fails_with_incorrect_subscriber_credentials(self):
	"""
	Algo:
        1.Create a vSG VM in compute node
        2.Create a vCPE container in vSG VM
        3.Ensure VM and containers created properly
        4.Configure a subscriber in XOS and assign a service id
        5.Verify subscriber successfully configured
        6.Now add devices( Mac addresses ) under the subscriber admin group
        7.Verify all devices ( Macs ) added successfully
	8.Login vCPE with credentials with which subscriber configured
	9.Verify subscriber successfully logged in
	10.Logout and login again with incorrect credentials ( either user name or password )
	11.Verify login attempt to vCPE fails wtih incorrect credentials
	"""
    def test_vsg_for_subscriber_configuration_in_vcpe_retain_after_vcpe_restart(self):
        """
        Algo:
        1.Create a vSG VM in compute node
        2.Create a vCPE container in vSG VM
        3.Ensure VM and containers created properly
        4.Configure a subscriber in XOS  and assign a service id
        5.Verify subscriber successfully configured
        6.Now add devices( Mac addresses ) under the subscriber admin group
        7.Verify all devices ( Macs ) added successfully
        8.Restart vCPE ( locate backup config path while restart )
        9.Verify subscriber details in vCPE after restart should be same as before the restart
        """
    def test_vsg_for_create_multiple_vcpe_instances_and_configure_subscriber_in_each_instance(self):
        """
        Algo:
        1.Create a vSG VM in compute node
        2.Create 2 vCPE containers in vSG VM
        3.Ensure VM and containers created properly
        4.Configure a subscriber in XOS for each vCPE instance and assign a service id
        5.Verify subscribers successfully configured
	6.Now login vCPE-2 with subscriber-1 credentials
	7.Verify login fails
	8.Now login vCPE-1 with subscriber-2 credentials
	9.Verify login fails
	10.Now login vCPE-1 with subscriber-1 and vCPE-2 with  subscriber-2 credentials
	11.Verify that both the subscribers able to login to their respective vCPE containers
	"""
    def test_vsg_for_same_subscriber_can_be_configured_for_multiple_services(self):
        """
        Algo:
        1.Create 2 vSG VMs in compute node
        2.Create a vCPE container in each vSG VM
        3.Ensure VMs and containers created properly
        4.Configure same subscriber in XOS for each vCPE instance and assign a service id
        5.Verify subscriber successfully configured
        6.Now login vCPE-1 with subscriber credentials
        7.Verify login success
        8.Now login vCPE-2 with the same subscriber credentials
        9.Verify login success
        """

    #Test Example Service
    def test_vsg_for_subcriber_avail_example_service_running_in_apache_server(self):
	"""
	Algo:
        1.Create a vSG VM in compute node
        2.Create a vCPE container in each vSG VM
        3.Ensure VM and container created properly
        4.Configure a subscriber in XOS for the vCPE instance and assign a service id
	5.On-board an example service into cord pod
	6.Create a VM in compute node and run the example service ( Apache server )
	7.Configure the example service with service specific and subscriber specific messages
	8.Verify example service on-boarded successfully
	9.Verify example service running in VM
	10.Run a curl command from subscriber to reach example service
	11.Verify subscriber can successfully reach example service via vSG
	12.Verify that service specific and subscriber specific messages
	"""
    def test_vsg_for_subcriber_avail_example_service_running_in_apache_server_after_service_restart(self):
        """
        Algo:
        1.Create a vSG VM in compute node
        2.Create a vCPE container in each vSG VM
        3.Ensure VM and container created properly
        4.Configure a subscriber in XOS for the vCPE instance and assign a service id
        5.On-board an example service into cord pod
        6.Create a VM in compute node and run the example service ( Apache server )
        7.Configure the example service with service specific and subscriber specific messages
        8.Verify example service on-boarded successfully
        9.Verify example service running in VM
        10.Run a curl command from subscriber to reach example service
        11.Verify subscriber can successfully reach example service via vSG
        12.Verify that service specific and subscriber specific messages
	13.Restart example service running in VM
	14.Repeat step 10
	15.Verify the same results as mentioned in steps 11, 12
        """

    #vCPE Firewall Functionality
    def test_vsg_firewall_for_creating_acl_rule_based_on_source_ip(self):
        """
        Algo:
        1.Create a vSG VM in compute node
        2.Create vCPE container in the VM
        3.Ensure vSG VM and vCPE container created properly
        4.Configure ac acl rule in vCPE to deny IP traffic from a source IP
        5.Bound the acl rule to WAN interface of  vCPE
        6.Verify configuration in vCPE is success
        8.Verify flows added in OvS
        """
    def test_vsg_firewall_for_creating_acl_rule_based_on_destination_ip(self):
        """
        Algo:
        1.Create a vSG VM in compute node
        2.Create vCPE container in the VM
        3.Ensure vSG VM and vCPE container created properly
        4.Configure ac acl rule in vCPE to deny IP traffic to a destination ip
        5.Bound the acl rule to WAN interface of  vCPE
        6.Verify configuration in vCPE is success
        8.Verify flows added in OvS
        """
    def test_vsg_firewall_for_acl_deny_rule_based_on_source_ip_traffic(self):
	"""
	Algo:
	1.Create a vSG VM in compute node
	2.Create vCPE container in the VM
	3.Ensure vSG VM and vCPE container created properly
	4.Configure ac acl rule in vCPE to deny IP traffic from a source IP
	5.Bound the acl rule to WAN interface of  vCPE
	6.From subscriber, send ping to the denied IP address
	7.Verify that ping fails as vCPE denies ping response
	8.Verify flows added in OvS
	"""
    def test_vsg_firewall_for_acl_deny_rule_based_on_destination_ip_traffic(self):
        """
        Algo:
        1.Create a vSG VM in compute node
        2.Create vCPE container in the VM
        3.Ensure vSG VM and vCPE container created properly
        4.Configure ac acl rule in vCPE to deny IP traffic to a destination IP
        5.Bound the acl rule to WAN interface of  vCPE
        6.From subscriber, send ping to the denied IP address
        7.Verify that ping fails as vCPE drops the ping request at WAN interface
        8.Verify flows added in OvS
        """

    def test_vsg_dnsmasq(self):
        pass

    def test_vsg_with_external_parental_control_family_shield_for_filter(self):
        pass

    def test_vsg_with_external_parental_control_with_answerx(self):
        pass

    def test_vsg_for_subscriber_upstream_bandwidth(self):
        pass

    def test_vsg_for_subscriber_downstream_bandwidth(self):
        pass

    def test_vsg_for_diagnostic_run_of_traceroute(self):
        pass

    def test_vsg_for_diagnostic_run_of_tcpdump(self):
        pass

    def test_vsg_for_iptable_rules(self):
        pass

    def test_vsg_for_iptables_with_neutron(self):
        pass
