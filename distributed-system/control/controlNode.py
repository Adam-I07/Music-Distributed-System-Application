from datetime import datetime
from controlNetworkInterface import controlNetworkInterface
import threading
import sys
import subprocess
import os, re
import socket

node_port = 50001


class abstractControl:
    def __init__(self, host="10.30.8.62", port=50001):
        self.host = host
        self.port = port
        self.networkHandler = controlNetworkInterface()
        self.connection = None
        self.uiThread = threading.Thread(target=self.ui)
        self.is_running = True
        self.node_IP = self.get_node_address()
        print(f"Control Node is is_running on: {self.node_IP}")

    # Simple UI thread
    def ui(self):
        # Handle incoming commands from the server - at the moment that is simply "display them to the user"
        while self.is_running:
            if self.connection:
                command = self.connection.iBuffer.get()
                if command:
                    if command.startswith("cmd"):
                        print()
                        command_split = command.split(":")
                        if len(command_split) >= 3 and command_split[0] == "cmd":
                            if len(command_split) >= 3:
                                node_to_spawn = command_split[2]
                                print(f"Bootstrap requested spawning of node: {node_to_spawn}")
                                if node_to_spawn == "auth":
                                    print("Spawning authentication node")
                                    DETACHED_PROCESS = 0x00000008
                                    pid = subprocess.Popen([sys.executable, "../authentication/authenticationNode.py"],
                                                           creationflags=subprocess.CREATE_NEW_CONSOLE |
                                                                         subprocess.CREATE_NEW_PROCESS_GROUP).pid

                                if node_to_spawn == "fdn":
                                    print("Spawning file distribution node")
                                    DETACHED_PROCESS = 0x00000008
                                    pid = subprocess.Popen([sys.executable, "../fileDistribution/fileDistributionNode.py"],
                                                           creationflags=subprocess.CREATE_NEW_CONSOLE |
                                                                         subprocess.CREATE_NEW_PROCESS_GROUP).pid
                            else:
                                print("Invalid command sent.")
                        else:
                            print("Invalid command sent")

    def process(self): 
        global node_port
        self.uiThread.start()
        self.connection = self.networkHandler.start_control(self.host, self.port)

        while self.is_running:
            command = "control:cmd:spawn:" + str(self.node_IP) + ":" + str(self.port)
            if self.connection:
                self.connection.oBuffer.put(command)
                command = input()

        self.networkHandler.quit()
        self.uiThread.join()

    def get_node_address(self):
        try:
            addresses = os.popen(
                'IPCONFIG | FINDSTR /R "Ethernet adapter Local Area Connection .* Address.*[0-9][0-9]*\.[0-9]['
                '0-9]*\.[0-9][0-9]*\.[0-9][0-9]*"')
            ip_list = re.findall(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', addresses.read())

            # Filter and sort the IP addresses
            filtered_ips = [ip for ip in ip_list if
                            ip.startswith('10.') and not ip.endswith('.0') and not ip.endswith('.254')]

            if filtered_ips:
                # Return host
                return filtered_ips[0]
            else:
                # Return local host
                host_name = socket.gethostname()
                # Get the local IP address by resolving the host name
                local_ip = socket.gethostbyname(host_name)
                return local_ip
        except:
            pass


if __name__ == "__main__":
    controlNode = abstractControl("10.30.8.62", 50001)
    controlNode.process()
