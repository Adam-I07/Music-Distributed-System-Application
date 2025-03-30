import socket
import threading
from clientConnectionHandler import clientConnectionHandler
from enum import Enum

class Role(Enum):
    CLIENT = 2

class clientNetworkInterface:
    def __init__(self):
        self.listeners = []
        self.connectionHandler = clientConnectionHandler()
        self.running = True

    # Start client
    def start_client(self, ip, port, duration=20, retries=30):
        # Modification starts here
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Variables to track the connection attempts
        connected = False
        attempts = 0
        # Set the timeout on the socket to 1s - this is how long we will wait for a response
        conn.settimeout(duration)

        # Attempting to establish connection with server, will keep retrying
        while not connected and attempts < retries:
            try:
                print("Attempting to establish connection to bootstrap.")
                conn.connect((ip, port))
                connected = True
            except socket.error:
                attempts += 1
        if connected:
            return self.connectionHandler.add_connection(conn)
        return None

    def get_message(self, ip=None, port=None):
        return self.connectionHandler.get_message(ip, port)

    def push_message(self, message, ip=None, port=None):
        return self.connectionHandler.push_message(ip, port, message)

    def quit(self):
        self.connectionHandler.quit()
        self.running = False
        for listener in self.listeners:
            listener.join()
