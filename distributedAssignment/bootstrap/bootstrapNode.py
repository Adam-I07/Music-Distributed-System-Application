from collections import deque
from serverNetworkInterface import serverNetworkInterface
import time
from datetime import datetime
import threading
import os
import json

connected_clients = 0
control_node = 0
control_nodes = [] 
authentication_nodes = [] 
authentication_microservice_nodes = []  
file_distribution_nodes = []
file_distribution_microservice_nodes = []  
client_tokens = []     
clients = []            


class FunctionalityHandler:
    def __init__(self, network):
        self.network = network
        self.running = True
        self.connections = []
        self.clientConnection = None
        self.load_balancer_tasks = deque()
        self.load_balancer_lock = threading.Lock()
        self.max_concurrent_tasks = 3
        self.current_tasks = 0
        self.client_limit = 6
        thread = threading.Thread(target=self.connected_nodes_stats)
        thread.start()

    def process(self, ip, port, connection=None):
        self.connected_client = None
        while self.running:
            global connected_clients
            if connection:
                self.update_heartbeat(connection, ip, port)
                try:
                    global control_nodes
                    global clients
                    if not connection.iBuffer.empty():
                        message = connection.iBuffer.get()
                        global client_tokens
                        if message:
                            global client_tokens
                            global clients
                            global file_distribution_microservice_nodes
                            ip, port = connection.sock.getpeername()
                            if message.startswith("ping"):
                                connection.oBuffer.put("pong")
                            elif message.startswith("quit"):
                                print(f"Connection closed {self.ip}:{self.port} has been disconnected", end="")
                                self.find_connection(connection, ip, port)
                                self.connections.remove(connection)
                                print()
                                exit()
                            elif message.startswith("client"):
                                cmdparts = message.split(":")
                                if len(cmdparts) >= 3:
                                    if cmdparts[1] == "cmd":
                                        if cmdparts[2] == "start_menu":
                                            print("recieved command to connect to authentication node from client")
                                            command_value = cmdparts[3]
                                            if command_value == '1' or command_value == '2':
                                                connected_clients += 1
                                                if len(authentication_microservice_nodes) < 1:
                                                    connection.oBuffer.put(f"bootstrap:cmd:auth:-1")
                                                elif len(authentication_microservice_nodes) >= 1:
                                                    self.connected_client = connection
                                                    self.load_balancer("authentication", connection, ip, port, connection)
                                            else:
                                                connection.oBuffer.put(f"bootstrap:cmd:auth:-1")
                                        elif cmdparts[2] == "fdn":
                                            user_auth_token_founs = False
                                            print()
                                            print(f"Received request to connect to file distribution from client")
                                            user_token_to_search = cmdparts[3]
                                            for token in enumerate(client_tokens):
                                                if token == user_token_to_search:
                                                    print(f"User Authentication token found. Authentication toke: {user_token_to_search}")
                                                    user_auth_token_founs = True
                                                    break
                                            if user_auth_token_founs:
                                                print()
                                                print("Authentication Token found and user is given access to file distribution node")
                                                self.load_balancer("filedistribution", connection, ip, port, connection)
                                            else:
                                                print()
                                                print("Token not found")
                                                self.clientConnection = connection
                                                self.load_balancer("confirm_token", connection, ip, port, user_token_to_search)
                                        elif cmdparts[2] == "spwn":
                                            print(f"New client connected on: {ip}:{port}")
                                            client = Clients(connection, ip, port)
                                            clients.append(client)
                                        else:
                                            print("Invalid command")
                            elif message.startswith("control"):
                                cmdparts = message.split(":")
                                if len(cmdparts) >= 3:
                                    if cmdparts[1] == "cmd":
                                        if cmdparts[2] == "spawn":
                                            print(f"New control node connected")
                                            name = "control"
                                            self.load_balancer("control", connection, ip, port, None)
                                        else:
                                            print("error")
                                    else:
                                        print("error")
                                else:
                                    print("error")
                            elif message.startswith("auth"):
                                print()
                                cmdparts = message.split(":")
                                if len(cmdparts) >= 3:
                                    if cmdparts[1] == "cmd":
                                        if cmdparts[2] == "load":
                                            print(f"New Authentication node connection added")
                                            print()
                                            name = "auth"
                                            self.auth_fdn_handling(connection, name, ip, port)
                                            global authentication_nodes
                                            authentication_nodes.append(Nodes(len(authentication_nodes) + 1, "auth_" + str(len(authentication_microservice_nodes) + 1), connection, ip, port))
                                            connection.oBuffer.put("cmd:spwn:ms")
                                        elif cmdparts[2] == "spwnms":
                                            print("New authenticaton microservice command added")
                                            ip = cmdparts[3]
                                            port = cmdparts[4]
                                            name = "auth-ms"
                                            self.auth_fdn_handling(connection, name, ip, port)
                                            authentication_microservice_nodes.append(Nodes(len(authentication_microservice_nodes) + 1, "auth_ms_" + str(len(authentication_microservice_nodes) + 1), None, ip, port))
                                        elif cmdparts[2] == "token":
                                            status = cmdparts[3]
                                            token = cmdparts[4]
                                            if status == "0":
                                                print(f"Authentication token validated: {cmdparts[4]}")
                                                client_tokens.append(token)
                                                if len(file_distribution_microservice_nodes) < 1:
                                                    self.clientConnection.oBuffer.put(f"bootstrap:cmd:fdn:-1")
                                                    if len(control_nodes) == 1:
                                                        node = control_nodes[0]
                                                        self.load_balancer("control", node.connection, ip, port, None)

                                                elif len(file_distribution_microservice_nodes) >= 1:
                                                    self.load_balancer("filedistribution",self.clientConnection, ip, port, self.connected_client)
                                            else:
                                                print("Authentication token received was invalid")
                                                connection.oBuffer.put(f"bootstrap:cmd:token:-1")
                            elif message.startswith("fdn"):
                                print()
                                cmdparts = message.split(":")
                                global file_distribution_nodes
                                if len(cmdparts) >= 3:
                                    if cmdparts[1] == "cmd":
                                        if cmdparts[2] == "load":
                                            print(f"New file distribution node added")
                                            print()
                                            name = "fdn"
                                            self.auth_fdn_handling(connection, name, ip, port)
                                            file_distribution_nodes.append(Nodes(len(file_distribution_nodes) + 1, "fdn_" + str(len(file_distribution_microservice_nodes) + 1), connection, ip, port))
                                            connection.oBuffer.put("cmd:spwn:ms")
                                        elif cmdparts[2] == "spwnms":
                                            print("New file distribution microservice was added")
                                            ip = cmdparts[3]
                                            port = cmdparts[4]
                                            name = "fdn-ms"
                                            self.auth_fdn_handling(connection, name, ip, port)
                                            file_distribution_microservice_nodes.append(Nodes(len(file_distribution_microservice_nodes) + 1, "fdn_ms_" + str(len(file_distribution_microservice_nodes) + 1), connection, ip, port))
                            else:
                                connection.oBuffer.put(f"Echoing: {message}")
                except ConnectionResetError:
                    self.connections.remove(connection)
                    break
        self.network.quit()

    def execute_task(self, command, connection, ip, port, extra):
        global control_node
        global control_nodes
        global connected_clients
        amount_of_authentication = 0
        amount_of_file_distribution = 0

        for nodes in control_nodes:
            if "authentication" in nodes.functionalNodes:
                amount_of_authentication += 1
            if "filedistribution" in nodes.functionalNodes:
                amount_of_file_distribution += 1
        print(f"Nodes available: authentication nodes:{amount_of_authentication}, file distribution node:{amount_of_file_distribution} and control nodes: {len(control_nodes)}")
        if command == "control":
            if control_node == 0:
                control_node += 1
                control_node_type = controlNodes(connection, ip, port, "authentication")
                print("Assigning first control node to become an authentication node")
                connection.oBuffer.put("cmd:node:auth")
                control_nodes.append(control_node_type)
                control_node_type.display_info()
            elif control_node >= 1:
                if amount_of_authentication >= 1 and amount_of_file_distribution < 1:
                    if amount_of_file_distribution == 0:
                        control_node += 1
                        control_node_type = controlNodes(connection, ip, port, "filedistribution")
                        print(f"Assigning control node to become an file distribution node")
                        connection.oBuffer.put("cmd:node:fdn")
                        control_nodes.append(control_node_type)
                        control_node_type.display_info()
                elif amount_of_authentication < 1 <= amount_of_file_distribution:
                    control_node += 1
                    control_node_type = controlNodes(connection, ip, port, "authentication")
                    print(f"Assigning control node to become an authentication node")
                    connection.oBuffer.put("cmd:node:auth")
                    control_nodes.append(control_node_type)
                    control_node_type.display_info()
                elif amount_of_authentication >= 1 and amount_of_file_distribution >= 1:
                    print(f"Extra control node detected")
                    control_node += 1
                    if amount_of_authentication == amount_of_file_distribution:
                        print(f"Assigning control node to become an authentication node")
                        control_node_type = controlNodes(connection, ip, port, "authentication")
                        connection.oBuffer.put("cmd:node:auth")
                        control_nodes.append(control_node_type)
                        control_node_type.display_info()
                    elif amount_of_authentication > amount_of_file_distribution:
                        print(f"Assigning control node to become an file distribution node")
                        control_node_type = controlNodes(connection, ip, port, "filedistribution")
                        connection.oBuffer.put("cmd:node:fdn")
                        control_nodes.append(control_node_type)
                        control_node_type.display_info()
            self.auth_fdn_handling(connection, 'control', ip, port)
        elif command == 'confirm_token':
            global authentication_nodes
            if len(authentication_nodes) > 0 and len(authentication_nodes) <= 1:
                print("Checking authentication token with authentication node")
                auth_node = authentication_nodes[0]
                auth_connection = auth_node.connection
                token = extra
                auth_connection.oBuffer.put(f"cmd:check:token:{token}")
        elif command == "authentication":
            if connected_clients <= self.client_limit:
                auth_microservice = authentication_microservice_nodes[0]
                if extra not in auth_microservice.connectedClients:
                    auth_microservice.connectedClients.append(extra)
                else:
                    print(f"client token: {extra}, already exists in connectedClients")
                name = "auth-ms"
                auth_ms_connection = f"{auth_microservice.nodeNumber}:{name}:{auth_microservice.ip}:{auth_microservice.port}"
                connection.oBuffer.put(f"bootstrap:cmd:auth:0:{auth_ms_connection}")
            elif connected_clients > self.client_limit:
                print("Client limit reached")
        elif command == "filedistribution":
            if connected_clients <= self.client_limit:
                try:
                    fdn_microservice = file_distribution_microservice_nodes[0]
                    fdn_microservice.connectedClients.append(extra)
                    name = "fd-ms"
                    fdn_ms_connection = f"{fdn_microservice.nodeNumber}:{name}:{fdn_microservice.ip}:{fdn_microservice.port}"
                    connection.oBuffer.put(f"bootstrap:cmd:fdn:0:{fdn_ms_connection}")
                except:
                    print("No File distribution node available")
                    connection.oBuffer.put(f"bootstrap:cmd:fdn:-1")
            elif connected_clients > self.client_limit:
                print("more than 5 connected clients")
        print("Bootstrap Task Ended")
        time.sleep(1)
        with self.load_balancer_lock:
            self.current_tasks -= 1
        self.load_balancer_execution()
        return

    def auth_fdn_handling(self, connection, name, ip, port):
        condition = connection.add_connection_node(name, ip, port)
        if condition:
            print(f"{name} node connected on: {ip}:{port} and has been added")
        else:
            print(f"{name} node joined on {ip}:{port} was not added due to an error", end="")
        print()

    
    def load_balancer(self, command, connection, ip, port, extra):
        self.load_balancer_tasks.append((command, connection, ip, port, extra))
        self.load_balancer_execution()

    def load_balancer_execution(self):
        with self.load_balancer_lock:
            if self.current_tasks >= self.max_concurrent_tasks:
                return

            if self.load_balancer_tasks:
                command, connection, ip, port, extra = self.load_balancer_tasks.popleft()
                threading.Thread(target=self.execute_task, args=(command, connection, ip, port, extra)).start()
                self.current_tasks += 1

    def add(self, connection, ip, port):
        self.connections.append(connection)
        handler_thread = threading.Thread(target=self.process, args=(ip, port, connection,))
        handler_thread.start()

    def update_heartbeat(self, connection, ip, port):
        last_message_time_past = connection.time_since_last_message()
        self.ip = ip
        self.port = port
        if last_message_time_past > 5:
            connection.update_time()
            connection.add_timeout()
            try:
                ip, port = connection.sock.getpeername()
            except OSError as e:
                if e.errno == 10038: 
                    print()
                    print(f"Connection closed {ip}:{port}.")
                    self.find_connection(connection, ip, port)
                    self.connections.remove(connection)
                    print()
                    exit()

    def connected_nodes_stats(self):
        while True:
            global clients
            global control_nodes

            if all(not array for array in
                   [control_nodes, authentication_nodes, authentication_microservice_nodes, file_distribution_nodes, file_distribution_microservice_nodes, client_tokens, clients]):
                print(f"No nodes are attempting to connect.")
                pass
            else:
                print()
                print(f"Connected nodes information: \n"
                      f"Connected clients: {len(clients)}\n"
                      f"Connected Control nodes: {len(control_nodes)}")
                for index, control in enumerate(control_nodes):
                    print(f"Control node: {index+1}\n"
                          f"    {control.ip}:{control.port}\n"
                          f"    sub: {control.functionalNodes}")
                for index, authentication in enumerate(authentication_nodes):
                    print(f"Authentication node: {index+1} - {authentication.ip}:{authentication.port}")
                for index, file_distribution in enumerate(file_distribution_nodes):
                    print(f"File distribution node: {index+1} - {file_distribution.ip}:{file_distribution.port}")
                for index, authentication_microservice in enumerate(authentication_microservice_nodes):
                    print(f"Authentication microservice: {index+1}\n"
                          f"    {authentication_microservice.ip}:{authentication_microservice.port}\n"
                          f"    Connected clients: {len(authentication_microservice.connectedClients)}")
                for index, file_distribution_microservice in enumerate(file_distribution_microservice_nodes):
                    print(f"File distribution microservice: {index+1}\n"
                          f"    {file_distribution_microservice.ip}:{file_distribution_microservice.port}\n"
                          f"    Connected clients: {len(file_distribution_microservice.connectedClients)}")
                pass
            time.sleep(10)

    def find_connection(self, connection, ip, port):
        global clients
        global connected_clients
        global control_node
        global control_nodes
        global authentication_nodes
        global file_distribution_nodes

        for client in clients:
            if (client.connection == connection and client.ip == ip and client.port == port):
                print()
                print(f"Client disconnected: {ip}:{port}.")

                for authentication_node in authentication_microservice_nodes:
                    # Check the connectedClients array for the condition
                    for client_connection in authentication_node.connectedClients:
                        if client_connection == connection:
                            print()
                            print(f"Client successfully removed from Authentication Microservice")
                            authentication_node.connectedClients.remove(client_connection)
                for file_distribution_node in file_distribution_microservice_nodes:
                    # Check the connectedClients array for the condition
                    for client_connection in file_distribution_node.connectedClients:
                        if client_connection == connection:
                            print()
                            print(f"Client successfully removed from File Distribution Microservice")
                            file_distribution_node.connectedClients.remove(client_connection)

                connected_clients -= 1
                clients.remove(client)

        for control in control_nodes:
            if (control.connection == connection and control.ip == ip and control.port == port):
                print()
                print(f"control node {ip}:{port} has been disconnected")
                control_nodes.remove(control)
                control_node -= 1
        
        for file_distribution in file_distribution_nodes:
            if (file_distribution.connection == connection):
                print()
                print(f"File distribution node  {ip}:{port} hsd been disconnected")
                file_distribution_nodes.remove(file_distribution)


        for authentication in authentication_nodes:
            if (authentication.connection == connection):
                print()
                print(f"Authentication node {ip}:{port} has been disconnected")
                authentication_nodes.remove(authentication)

class AbstractServer:
    def __init__(self, host="10.30.8.62", port=50001):
        self.networkHandler = serverNetworkInterface()
        self.functionalityHandler = FunctionalityHandler(self.networkHandler)
        self.host = host
        self.port = port
        print(f"Bootstrap node started on {self.host}:{self.port}")
        print("Waiting for nodes to connect.")

    def client_handler(self, clientConnection):
        self.functionalityHandler.add(clientConnection, self.host, self.port)

    def process(self):
        self.create_json_for_connection_recording()
        self.networkHandler.start_server(self.host, self.port, self.client_handler)

    def create_json_for_connection_recording(self):
        filename='connected_nodes_information.json'
        if os.path.exists(filename):
            os.remove(filename)
        with open(filename, 'w') as file:
            data = {"connections": []}
            json.dump(data, file, indent=2)


class controlNodes:
    def __init__(self, connection, ip, port, functionalNodeType):
        self.connection = connection
        self.ip = ip
        self.port = port
        self.functionalNodes = functionalNodeType

    def display_info(self):
        print("Control Node:")
        print(f"IP Address: {self.ip}")
        print(f"Port Number: {self.port}")
        print(f"Functional: {self.functionalNodes}")


class Clients:
    def __init__(self, connection, ip, port):
        self.connection = connection
        self.ip = ip
        self.port = port

    def display_info(self):
        print("Client:")
        print(f"IP Address: {self.ip}")
        print(f"Port Number: {self.port}")


class Nodes:
    def __init__(self, nodeNumber, nodeType, connection, ip, port):
        self.nodeNumber = nodeNumber
        self.nodeType = nodeType
        self.connection = connection
        self.ip = ip
        self.port = port
        self.connectedClients = []

    def display_info(self):
        print("Nodes")
        print(f"Control Number: {self.nodeNumber}")
        print(f"Node type: {self.nodeType}")
        print(f"IP Address: {self.ip}")
        print(f"Port Number: {self.port}")

if __name__ == "__main__":
    server = AbstractServer("10.30.8.62", 50001)
    server.process()
