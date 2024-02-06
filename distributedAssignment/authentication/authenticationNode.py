import os
import subprocess
import sys
import time
from collections import deque
from datetime import datetime
from authenticationNetworkInterface import authenticationNetworkInterface
import threading
import os, re
import socket

auth_microservice_count = 0

class abstractAuthentication:
    def __init__(self, host="10.30.8.62", port=50001):
        self.host = host
        self.port = port
        self.available_ports = 50001
        self.network_handler = authenticationNetworkInterface()
        self.connection = None
        self.ui_thread = threading.Thread(target=self.ui)
        self.connected_clients = 0
        self.is_running = True
        self.node_IP = self.get_node_address()
        self.load_balancer_tasks = deque()
        self.load_balancer_lock = threading.Lock()
        self.current_ruinning_tasks = 0
        self.maximum_num_of_concurrent_tasks_to_run = 2
        print(f"Authentication node is running on: {self.node_IP}")

    # Simple UI thread
    def ui(self):
        while self.is_running:
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
                                        self.authentication_load_balancer(parts[1], None)
                                if after_node == "check":
                                    if parts[2] == "token":
                                        # Check client token
                                        client_token = parts[3]
                                        print(f"Client Token received from bootstrap: {client_token}")
                                        self.authentication_load_balancer(parts[1], client_token)

    def process(self):
        # Start the UI thread and start the network components
        self.ui_thread.start()
        self.connection = self.network_handler.start_authentication(self.host, self.port)

        command = "auth:cmd:load:" + str(self.node_IP) + ":" + str(self.available_ports)
        self.available_ports += 1
        self.connection.oBuffer.put(command)

        while self.is_running:
            if self.connection:
                command = input()

        # stop the network components and the UI thread
        self.network_handler.quit()
        self.ui_thread.join()

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
                # Get local host
                host_name = socket.gethostname()
                # Get the local IP address by resolving the host name
                local_ip = socket.gethostbyname(host_name)
                return local_ip
        except:
            pass

    def authentication_load_balancer(self, command, extra):
        self.load_balancer_tasks.append((command, extra))
        self.execute_load_balancer()

    def execute_load_balancer(self):
        with self.load_balancer_lock:
            # Check if the maximum number of concurrent tasks is reached
            if self.current_ruinning_tasks >= self.maximum_num_of_concurrent_tasks_to_run:
                return

            if self.load_balancer_tasks:
                command, extra = self.load_balancer_tasks.popleft()

                # Execute the task in a separate thread
                threading.Thread(target=self.execute_task, args=(command, extra)).start()
                self.current_ruinning_tasks += 1

    def execute_task(self, command, extra):
        global auth_microservice_count
        if command == "spwn":
            if auth_microservice_count == 0:
                time.sleep(2)
                self.spawn_microservices()
        elif command == "check":
            client_token = extra
            if self.check_token_exists(client_token):
                print(f"Client token valid")
                token_response = f"auth:cmd:token:0:{client_token}"
            else:
                print(f"Client token not valid")
                token_response = f"auth:cmd:token:-1"
            self.connection.oBuffer.put(token_response)
        time.sleep(1)

        with self.load_balancer_lock:
            self.current_ruinning_tasks -= 1
        self.execute_load_balancer()
        return

    def spawn_microservices(self):
        print("Spawning authentication microservice")
        try:
            DETACHED_PROCESS = 0x00000008
            microservice_ip = self.node_IP
            microservice_port = str(self.available_ports)
            self.available_ports += 1
            try:
                auth_microservice_processes = subprocess.Popen(
                    [
                        sys.executable,
                        "../authentication/authenticationMicroservice.py",
                        microservice_ip,
                        microservice_port
                    ],
                    creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NEW_PROCESS_GROUP
                ).pid
            except Exception as ee:
                print(f"Error : {ee}")
            command = "auth:cmd:spwnms:" + str(microservice_ip) +":"+ str(microservice_port)
            if self.connection:
                self.connection.oBuffer.put(command)
        except Exception as ex:
            print(f"Errors: {ex}")
            pass
    
    def ping_thread_delayed_start(self):
        print()
        self.pingThread = threading.Thread(target=self.ping)
        self.pingThread.daemon = True
        self.pingThread.start()

    def start_ping_thread(self):
        threading.Timer(8, self.ping_thread_delayed_start).start()


    def ping(self):
        start_time = time.time()
        execution_time = time.time() - start_time
        timer_delay = max(0, (5 - execution_time))

        if self.is_running:
            threading.Timer(timer_delay, self.ping).start()

    def check_token_exists(self, token_to_find):
        try:
            current_location = os.path.dirname(os.path.abspath(__file__))
            user_records = os.path.join(current_location, 'userRecords.txt')
            with open(user_records, 'r') as file:
                for line in file:
                    if 'Token: ' in line:
                        token_in_file = line.split('Token: ')[1].strip()
                        if token_in_file == token_to_find:
                            return True 
            return False 
        except Exception as ex:
            print(ex)
            return False


if __name__ == "__main__":
    auth = abstractAuthentication("10.30.8.62", 50001)
    auth.process()
