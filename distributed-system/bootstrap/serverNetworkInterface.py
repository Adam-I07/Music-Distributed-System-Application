import socket
import threading
from serverConnectionHandler import serverConnectionHandler
from enum import Enum


class Role(Enum):
    SERVER = 1


class serverNetworkInterface:
    def __init__(self):
        self.listeners = []
        self.connectionHandler = serverConnectionHandler()
        self.running = True

    def start_server(self, ip, port, callbackHandler=None):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((ip, port))

        listener = threading.Thread(target=self.listen, args=(sock, callbackHandler))
        listener.start()
        self.listeners.append(listener)
        return True

    def listen(self, sock=None, callBackHandler=None):
        while self.running:
            # Set socket to listen for incoming connections, then block waiting for a connection
            sock.listen()
            conn, addr = sock.accept()
            conn.setblocking(False)
            connection = self.connectionHandler.add_connection(conn)
            callBackHandler(connection)

    def get_message(self, ip=None, port=None):
        return self.connectionHandler.get_message(ip, port)

    def push_message(self, message, ip=None, port=None):
        return self.connectionHandler.push_message(ip, port, message)

    def has_client(self):
        return self.connectionHandler.has_client()

    def get_clients(self):
        return self.connectionHandler.get_clients()

    def client_exists(self, ip, port):
        return self.connectionHandler.client_exists(ip,port)

    def quit(self):
        self.connectionHandler.quit()
        self.running = False
        for listener in self.listeners:
            listener.join()
