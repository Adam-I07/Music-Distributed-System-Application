import subprocess
import sys
import time
from collections import deque
from datetime import datetime
from  fileDistributionNetworkInterface import fileDistributionNetworkInterface
import threading
import os, re
import socket

fdn_microservice_count = 0

class abstractFileDistribution:
    def __init__(self, host="10.30.8.62", port=50001):
        self.host = host
        self.port = port
        self.available_ports = 50005
        self.networkHandler = fileDistributionNetworkInterface()
        self.connection = None
        self.uiThread = threading.Thread(target=self.ui)
        self.running = True
        self.nodeIp = self.get_node_address()
        self.load_balancer_tasks = deque()
        self.load_balancer_lock = threading.Lock()
        self.max_concurrent_tasks = 2
        self.current_tasks = 0
        print(f"File Distribution node is running on on: {self.nodeIp}")
        
    # Simple UI thread
    def ui(self):
        while self.running:
            if self.connection:
                command = self.connection.iBuffer.get()
                if command:
                    if command.startswith("cmd"):
                        parts = command.split(":")
                        if len(parts) >= 3 and parts[0] == "cmd":
                            if len(parts) >= 3:
                                after_node = parts[1]
                                if after_node == "spwn":
                                    after_node = parts[2]
                                    if after_node == "ms":
                                        print(f"Spawning file distribution microservice")
                                        self.file_distribution_load_balancer(parts[1], None)

    def process(self):
        # Start the UI thread and start the network components
        self.uiThread.start()
        self.connection = self.networkHandler.start_FDN(self.host, self.port)

        command = "fdn:cmd:load:" + str(self.nodeIp) + ":" + str(self.available_ports)
        self.available_ports += 1
        self.connection.oBuffer.put(command)

        while self.running:
            if self.connection:
                command = input()

        # stop the network components and the UI thread
        self.networkHandler.quit()

    def get_node_address(self):
        try:
            # Get local IP - needs IP starting with 10.x.x.x
            # Should return a list of all IP addresses - find one that starts 10. and isn't ended with .0 or .254
            addresses = os.popen(
                'IPCONFIG | FINDSTR /R "Ethernet adapter Local Area Connection .* Address.*[0-9][0-9]*\.[0-9]['
                '0-9]*\.[0-9][0-9]*\.[0-9][0-9]*"')
            ip_list = re.findall(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', addresses.read())

            # Filter and sort the IP addresses
            filtered_ips = [ip for ip in ip_list if
                            ip.startswith('10.') and not ip.endswith('.0') and not ip.endswith('.254')]

            if filtered_ips:
                # Return host if found
                return filtered_ips[0]
            else:
                # Return local host
                host_name = socket.gethostname()
                # Get the local IP address by resolving the host name
                local_ip = socket.gethostbyname(host_name)
                return local_ip
        except:
            pass

    def file_distribution_load_balancer(self, command, extra):
        self.load_balancer_tasks.append((command, extra))
        self.execute_load_balancer()

    def execute_load_balancer(self):
        with self.load_balancer_lock:
            if self.current_tasks >= self.max_concurrent_tasks:
                return

            if self.load_balancer_tasks:
                command, extra = self.load_balancer_tasks.popleft()

                threading.Thread(target=self.execute_task, args=(command, extra)).start()
                self.current_tasks += 1

    def execute_task(self, command, extra):
        global fdn_microservice_count
        if command == "spwn":
            if fdn_microservice_count == 0:
                time.sleep(2)
                self.spawn_microservices()

    def spawn_microservices(self):
        print("Spawning file distribution microservice")
        try:
            microservice_ip = self.nodeIp
            microservice_port = str(self.available_ports)
            self.available_ports += 1
            DETACHED_PROCESS = 0x00000008
            fdn_microservice_processes = subprocess.Popen(
                [
                    sys.executable,
                    "../fileDistribution/fileDistributionMicroservice.py",
                    microservice_ip,
                    microservice_port
                ],
                creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NEW_PROCESS_GROUP
            ).pid
            command = "fdn:cmd:spwnms:" + str(microservice_ip) + ":" + str(microservice_port)
            if self.connection:
                self.connection.oBuffer.put(command)
        except:
            pass

if __name__ == "__main__":
    FDN = abstractFileDistribution("10.30.8.62", 50001)
    FDN.process()